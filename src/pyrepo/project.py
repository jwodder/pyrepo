from contextlib import suppress
from functools import cached_property, partial, wraps
import logging
from pathlib import Path
import re
from shutil import rmtree
import sys
from typing import Any, Callable, Dict, Iterator, List, Optional, Union
import click
from in_place import InPlace
from jinja2 import Environment
from lineinfile import AfterLast, add_line_to_file
from packaging.specifiers import SpecifierSet
from pydantic import BaseModel, DirectoryPath
from . import git
from .changelog import Changelog, ChangelogSection
from .inspecting import InvalidProjectError, find_project_root, inspect_project
from .util import (
    PyVersion,
    get_jinja_env,
    map_lines,
    next_version,
    replace_group,
    runcmd,
    split_ini_sections,
    today,
)

log = logging.getLogger(__name__)


class Project(BaseModel):
    directory: DirectoryPath

    # All attributes from this point on are also context variables used by the
    # Jinja2 templates.

    #: The name of the project as it is/will be known on PyPI
    name: str

    version: str
    short_description: str
    author: str
    author_email: str
    install_requires: List[str]
    keywords: List[str]
    supports_pypy3: bool

    #: Extra testenvs to include runs for in CI, as a mapping from testenv name
    #: to Python version
    extra_testenvs: Dict[str, str]

    is_flat_module: bool
    import_name: str

    #: Sorted list of supported Python versions
    python_versions: List[PyVersion]

    python_requires: str

    #: Mapping from command (`console_scripts`) names to entry point
    #: specifications
    commands: Dict[str, str]

    github_user: str
    codecov_user: str
    repo_name: str
    rtfd_name: str
    has_tests: bool
    has_typing: bool
    has_doctests: bool
    has_docs: bool
    has_ci: bool
    has_pypi: bool
    copyright_years: List[int]
    default_branch: str

    class Config:
        # <https://github.com/samuelcolvin/pydantic/issues/1241>
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.python_versions.sort()

    @classmethod
    def from_directory(cls, dirpath: Optional[Path] = None) -> "Project":
        if dirpath is None:
            directory = Path()
        else:
            directory = Path(dirpath)
        return cls.from_inspection(directory, inspect_project(directory))

    @classmethod
    def from_inspection(cls, directory: Path, context: dict) -> "Project":
        return cls.parse_obj({"directory": directory.resolve(), **context})

    @property
    def initfile(self) -> Path:
        if self.is_flat_module:
            return self.directory / "src" / (self.import_name + ".py")
        else:
            return self.directory / "src" / self.import_name / "__init__.py"

    @cached_property
    def repo(self) -> git.Git:
        return git.Git(dirpath=self.directory)

    def get_template_context(self) -> dict:
        return self.dict(exclude={"directory"})

    def render_template(self, template_path: str, jinja_env: Environment) -> str:
        return (
            jinja_env.get_template(template_path + ".j2")
            .render(self.get_template_context())
            .rstrip()
            + "\n"
        )

    def write_template(
        self,
        template_path: str,
        jinja_env: Environment,
        force: bool = True,
    ) -> None:
        outpath = self.directory / template_path
        if not force and outpath.exists():
            log.info("File %s already exists; not templating", template_path)
            return
        log.info("Writing %s ...", template_path)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(
            self.render_template(template_path, jinja_env),
            encoding="utf-8",
        )

    def get_template_block(
        self, template_name: str, block_name: str, jinja_env: Environment
    ) -> str:
        tmpl = jinja_env.get_template(template_name)
        context = tmpl.new_context()
        return "".join(tmpl.blocks[block_name](context))

    def set_version(self, version: str) -> None:
        log.info("Setting __version__ to %r ...", version)
        map_lines(
            self.initfile,
            partial(
                replace_group,
                # Preserve quotation marks around version:
                r'^__version__\s*=\s*([\x27"])(?P<version>.+)\1\s*$',
                lambda _: version,
                group="version",
            ),
        )
        self.version = version

    def get_changelog_paths(
        self, docs: bool = False, extant: bool = True
    ) -> Iterator[Path]:
        paths: List[Union[str, Path]]
        if docs:
            paths = [Path("docs", "changelog.rst")]
        else:
            paths = ["CHANGELOG.md", "CHANGELOG.rst"]
        for p in paths:
            fpath = self.directory / p
            if not extant or fpath.exists():
                yield fpath

    def get_changelog(self, docs: bool = False) -> Optional[Changelog]:
        for p in self.get_changelog_paths(docs):
            with p.open(encoding="utf-8") as fp:
                return Changelog.load(fp)
        return None

    def set_changelog(self, value: Optional[Changelog], docs: bool = False) -> None:
        for p in self.get_changelog_paths(docs):
            if value is None:
                p.unlink()
            else:
                with p.open("w", encoding="utf-8") as fp:
                    value.dump(fp)
            return
        if value is not None:
            p = next(self.get_changelog_paths(docs, extant=False))
            with p.open("w", encoding="utf-8") as fp:
                value.dump(fp)

    def build(
        self, sdist: bool = True, wheel: bool = True, clean: bool = False
    ) -> None:
        if clean:
            with suppress(FileNotFoundError):
                rmtree(self.directory / "build")
            with suppress(FileNotFoundError):
                rmtree(self.directory / "dist")
        if sdist or wheel:
            args = []
            if sdist:
                args.append("--sdist")
            if wheel:
                args.append("--wheel")
            runcmd(sys.executable, "-m", "build", *args, self.directory)

    def unflatten(self) -> None:
        if not self.is_flat_module:
            log.info("Project is already a package; no need to unflatten")
            return
        log.info("Unflattening project ...")
        pkgdir = self.directory / "src" / self.import_name
        pkgdir.mkdir(parents=True, exist_ok=True)
        old_initfile = self.initfile
        new_initfile = pkgdir / "__init__.py"
        log.info(
            "Moving %s to %s ...",
            old_initfile.relative_to(self.directory),
            new_initfile.relative_to(self.directory),
        )
        old_initfile.rename(new_initfile)
        log.info("Updating setup.cfg ...")
        with InPlace(
            self.directory / "setup.cfg",
            mode="t",
            encoding="utf-8",
        ) as fp:
            in_options = False
            for ln in fp:
                if re.match(r"^py_modules\s*=", ln):
                    ln = "packages = find:\n"
                print(ln, end="", file=fp)
                if ln == "[options]\n":
                    in_options = True
                elif in_options and ln.isspace():
                    print("[options.packages.find]", file=fp)
                    print("where = src", file=fp)
                    print("", file=fp)
                    in_options = False
            if in_options:
                print("", file=fp)
                print("[options.packages.find]", file=fp)
                print("where = src", file=fp)
        self.is_flat_module = False

    def add_typing(self) -> None:
        log.info("Adding typing configuration ...")
        self.unflatten()
        log.info("Creating src/%s/py.typed ...", self.import_name)
        (self.directory / "src" / self.import_name / "py.typed").touch()
        jenv = get_jinja_env()
        log.info("Updating setup.cfg ...")
        with InPlace(
            self.directory / "setup.cfg",
            mode="t",
            encoding="utf-8",
        ) as fp:
            in_classifiers = False
            for ln in fp:
                if re.match(r"^classifiers\s*=", ln):
                    in_classifiers = True
                elif ln.isspace():
                    if in_classifiers:
                        print("    Typing :: Typed", file=fp)
                    in_classifiers = False
                print(ln, end="", file=fp)
            if in_classifiers:
                print("Typing :: Typed", file=fp)
            print(file=fp)
            print(
                self.get_template_block("setup.cfg.j2", "mypy", jenv),
                end="",
                file=fp,
            )
        if self.has_tests:
            log.info("Updating tox.ini ...")
            toxfile = self.directory / "tox.ini"
            sections = split_ini_sections(toxfile.read_text(encoding="utf-8"))
            with toxfile.open("w", encoding="utf-8") as fp:
                for sectname, sect in sections:
                    if sectname == "tox":
                        sect2 = replace_group(
                            re.compile(r"^envlist\s*=[ \t]*(.+)$", flags=re.M),
                            add_typing_env,
                            sect,
                        )
                        if sect == sect2:
                            raise RuntimeError("Could not find [tox]envlist in tox.ini")
                        sect = sect2
                    if sectname == "pytest":
                        print(
                            self.get_template_block(
                                "tox.ini.j2",
                                "testenv_typing",
                                jenv,
                            ),
                            file=fp,
                        )
                    print(sect, end="", file=fp)
        if self.has_ci:
            pyver = self.python_versions[0]
            log.info("Adding testenv %r with Python version %r", "typing", pyver)
            self.extra_testenvs["typing"] = str(pyver)
            self.write_template(".github/workflows/test.yml", jenv)
        self.has_typing = True

    def add_pyversion(self, v: str) -> None:
        pyv = PyVersion.parse(v)
        if str(pyv) not in SpecifierSet(self.python_requires):
            raise ValueError(
                f"Version {pyv} does not match python_requires ="
                f" {self.python_requires!r}"
            )
        log.info("Adding %s to supported Python versions", pyv)
        log.info("Updating setup.cfg ...")
        add_line_to_file(
            self.directory / "setup.cfg",
            f"    Programming Language :: Python :: {pyv}\n",
            inserter=AfterLast(r"^    Programming Language :: Python :: \d+\.\d+$"),
            encoding="utf-8",
        )
        if self.has_tests:
            log.info("Updating tox.ini ...")
            map_lines(
                self.directory / "tox.ini",
                partial(
                    replace_group,
                    re.compile(r"^envlist\s*=[ \t]*(.+)$", flags=re.M),
                    partial(add_py_env, pyv),
                ),
            )
        if self.has_ci:
            log.info("Updating .github/workflows/test.yml ...")
            add_line_to_file(
                self.directory / ".github" / "workflows" / "test.yml",
                f"{' ' * 10}- '{pyv}'\n",
                inserter=AfterLast(fr"^{' ' * 10}- ['\x22]?\d+\.\d+['\x22]?$"),
                encoding="utf-8",
            )

    def begin_dev(self) -> None:
        log.info("Preparing for work on next version ...")
        # Set __version__ to the next version number plus ".dev1"
        old_version = self.version
        new_version = next_version(old_version)
        self.set_version(new_version + ".dev1")
        # Add new section to top of CHANGELOGs
        new_sect = ChangelogSection(
            version="v" + new_version,
            date="in development",
            content="",
        )
        for docs in (False, True):
            if docs:
                if not (self.directory / "docs").exists():
                    continue
                log.info("Adding new section to docs/changelog.rst ...")
            else:
                log.info("Adding new section to CHANGELOG ...")
            chlog = self.get_changelog(docs=docs)
            if chlog is not None and chlog.sections:
                chlog.sections.insert(0, new_sect)
            else:
                chlog = Changelog(
                    intro="Changelog\n=========\n\n" if docs else "",
                    sections=[
                        new_sect,
                        ChangelogSection(
                            version="v" + old_version,
                            date=today(),
                            content="Initial release",
                        ),
                    ],
                )
            self.set_changelog(chlog, docs=docs)


def add_typing_env(envlist: str) -> str:
    envs = envlist.strip().split(",")
    envs.insert(envs[:1] == ["lint"], "typing")
    return ",".join(envs)


def add_py_env(pyv: PyVersion, envlist: str) -> str:
    envs = envlist.strip().split(",")
    if envs[-1:] == ["pypy3"]:
        envs.insert(-1, pyv.pyenv)
    else:
        envs.append(pyv.pyenv)
    return ",".join(envs)


def with_project(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        dirpath = find_project_root()
        if dirpath is None:
            raise click.UsageError("Not inside a project directory")
        try:
            project = Project.from_directory(dirpath)
        except InvalidProjectError as e:
            raise click.UsageError(str(e))
        return func(*args, project=project, **kwargs)

    return wrapped
