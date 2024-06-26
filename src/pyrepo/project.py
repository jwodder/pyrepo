from __future__ import annotations
from bisect import insort
from collections.abc import Callable, Iterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from functools import cached_property, partial, wraps
import logging
from pathlib import Path
import re
from shutil import rmtree
import sys
from typing import Any
import click
from configupdater import ConfigUpdater
from in_place import InPlace
from lineinfile import AfterLast, add_line_to_file
from packaging.specifiers import SpecifierSet
from . import git
from .changelog import Changelog, ChangelogSection
from .details import ProjectDetails
from .inspecting import InvalidProjectError, find_project_root
from .tmpltr import TemplateWriter
from .util import (
    PyVersion,
    map_lines,
    maybe_map_lines,
    next_version,
    replace_group,
    runcmd,
)

log = logging.getLogger(__name__)


@dataclass
class Project:
    directory: Path
    details: ProjectDetails

    @classmethod
    def from_directory(cls, dirpath: Path | None = None) -> Project:
        if dirpath is None:
            dirpath = Path()
        return cls(directory=dirpath, details=ProjectDetails.inspect(dirpath))

    @property
    def initfile(self) -> Path:
        if self.details.is_flat_module:
            return self.directory / f"{self.details.import_name}.py"
        else:
            return self.directory / "src" / self.details.import_name / "__init__.py"

    @cached_property
    def repo(self) -> git.Git:
        return git.Git(dirpath=self.directory)

    @property
    def private(self) -> bool:
        return any(c.startswith("Private") for c in self.details.classifiers)

    def get_template_writer(self) -> TemplateWriter:
        return TemplateWriter(context=self.details.for_json(), basedir=self.directory)

    def set_version(self, version: str) -> None:
        if not self.details.uses_versioningit:
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
        self.details.version = version

    def get_changelog_paths(
        self, docs: bool = False, extant: bool = True
    ) -> Iterator[Path]:
        paths: list[str | Path]
        if docs:
            paths = [Path("docs", "changelog.rst")]
        else:
            paths = ["CHANGELOG.md", "CHANGELOG.rst"]
        for p in paths:
            fpath = self.directory / p
            if not extant or fpath.exists():
                yield fpath

    def get_changelog(self, docs: bool = False) -> Changelog | None:
        for p in self.get_changelog_paths(docs):
            with p.open(encoding="utf-8") as fp:
                return Changelog.load(fp)
        return None

    def set_changelog(self, value: Changelog | None, docs: bool = False) -> None:
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
        if not self.details.is_flat_module:
            log.info("Project is already a package; no need to unflatten")
            return
        log.info("Unflattening project ...")
        pkgdir = self.directory / "src" / self.details.import_name
        pkgdir.mkdir(parents=True, exist_ok=True)
        old_initfile = self.initfile
        new_initfile = pkgdir / "__init__.py"
        log.info(
            "Moving %s to %s ...",
            old_initfile.relative_to(self.directory),
            new_initfile.relative_to(self.directory),
        )
        old_initfile.rename(new_initfile)
        import_name = self.details.import_name
        log.info("Updating pyproject.toml ...")
        with InPlace(self.directory / "pyproject.toml", encoding="utf-8") as fp:
            for line in fp:
                if re.match(r"path\s*=", line):
                    line = f'path = "src/{import_name}/__init__.py"\n'
                elif line.rstrip() == f'    "/{import_name}.py",':
                    line = '    "/src",\n'
                fp.write(line)  # noqa: B038
        if (self.directory / "tox.ini").exists():
            log.info("Updating tox.ini ...")
            with InPlace(self.directory / "tox.ini", encoding="utf-8") as fp:
                for line in fp:
                    line = re.sub(
                        rf"^(\s+(?:flake8|mypy)\s+){import_name}.py\b", r"\1src", line
                    )
                    if line.rstrip() == f"    {import_name}.py":
                        line = "    src\n"
                    elif line.rstrip() == f"    .tox/**/site-packages/{import_name}.py":
                        line = line.replace(f"/{import_name}.py", "")
                    print(line, end="", file=fp)
                    if re.match(r"sort_relative_in_force_sorted_sections\s*=", line):
                        print("src_paths = src", file=fp)
        self.details.is_flat_module = False

    def add_typing(self) -> None:
        if self.details.has_typing:
            log.info("Project already has typing; no need to add it")
            return
        log.info("Adding typing configuration ...")
        self.unflatten()
        log.info("Creating src/%s/py.typed ...", self.details.import_name)
        (self.directory / "src" / self.details.import_name / "py.typed").touch()
        templater = self.details.get_templater()
        log.info("Updating pyproject.toml ...")
        with InPlace(self.directory / "pyproject.toml", encoding="utf-8") as fp:
            in_classifiers = False
            for line in fp:
                if line == "classifiers = [\n":
                    in_classifiers = True
                elif in_classifiers and line == "]\n":
                    print('    "Typing :: Typed",', file=fp)
                    in_classifiers = False
                fp.write(line)  # noqa: B038
            mypy_cfg = templater.get_template_block("pyproject.toml.j2", "mypy")
            print(mypy_cfg, end="", file=fp)
        if self.details.has_tests:
            log.info("Updating tox.ini ...")
            toxfile = ConfigUpdater()
            toxfile.read(str(self.directory / "tox.ini"), encoding="utf-8")
            try:
                envlist = toxfile["tox"]["envlist"].value
            except KeyError:
                raise RuntimeError("Could not find [tox]envlist in tox.ini")
            else:
                assert envlist is not None
                toxfile["tox"]["envlist"].value = add_typing_env(envlist)
            testenv_typing = ConfigUpdater()
            testenv_typing.read_string(
                templater.get_template_block(
                    "tox.ini.j2",
                    "testenv_typing",
                    variables={"has_tests": self.details.has_tests},
                )
            )
            toxfile["pytest"].add_before.section(
                testenv_typing["testenv:typing"].detach()
            ).space()
            toxfile.update_file()
        if self.details.has_ci:
            self.add_ci_testenv("typing", str(self.details.python_versions[0]))
        self.details.has_typing = True

    def add_ci_testenv(self, testenv: str, pyver: str) -> None:
        log.info("Adding testenv %r with Python version %r", testenv, pyver)
        self.details.extra_testenvs[testenv] = pyver
        twriter = self.get_template_writer()
        twriter.write(".github/workflows/test.yml")
        if not (self.directory / ".github" / "dependabot.yml").exists():
            log.info("Creating Dependabot configuration")
            twriter.write(".github/dependabot.yml")
            log.warning("Please set up custom Dependabot labels separately")

    def add_pyversion(self, v: str) -> None:
        pyv = PyVersion.parse(v)
        if pyv in self.details.python_versions:
            log.info("Project already supports %s; not adding", pyv)
            return
        if str(pyv) not in SpecifierSet(self.details.python_requires):
            raise ValueError(
                f"Version {pyv} does not match python_requires ="
                f" {self.details.python_requires!r}"
            )
        log.info("Adding %s to supported Python versions", pyv)
        self.begin_dev(quiet=True)
        log.info("Updating pyproject.toml ...")
        add_line_to_file(
            self.directory / "pyproject.toml",
            f'    "Programming Language :: Python :: {pyv}",\n',
            inserter=AfterLast(r'^    "Programming Language :: Python :: \d+\.\d+",$'),
            encoding="utf-8",
        )
        if self.details.has_tests:
            log.info("Updating tox.ini ...")
            map_lines(
                self.directory / "tox.ini",
                partial(
                    replace_group,
                    re.compile(r"^envlist\s*=[ \t]*(.+)$"),
                    partial(add_py_env, pyv),
                ),
            )
        if self.details.has_ci:
            log.info("Updating .github/workflows/test.yml ...")
            add_line_to_file(
                self.directory / ".github" / "workflows" / "test.yml",
                f"{' ' * 10}- '{pyv}'\n",  # noqa: B028
                inserter=AfterLast(rf"^{' ' * 10}- ['\x22]?\d+\.\d+['\x22]?$"),
                encoding="utf-8",
            )
        self.update_latest_changelog_section(
            lambda items: add_pyversion_chlog(pyv, items)
        )
        insort(self.details.python_versions, pyv)

    def drop_pyversion(self) -> None:
        # TODO: Replace these errors with a custom class which the CLI logs at
        # ERROR level before exiting nonzero (or which get converted to Click
        # errors?)
        if not self.details.python_versions:
            raise ValueError("No supported Python versions to drop")
        elif len(self.details.python_versions) == 1:
            raise ValueError("Only one supported Python version; not dropping")
        dropver = self.details.python_versions.pop(0)
        log.info("Dropping %s from supported Python versions", dropver)
        self.begin_dev(quiet=True)
        newmin = self.details.python_versions[0]
        self.details.python_requires = re.sub(
            r"\d+(?:\.\d+)*", str(newmin), self.details.python_requires
        )
        log.info("Updating README.rst ...")
        map_lines(
            self.directory / "README.rst",
            partial(
                replace_group,
                re.compile(r"requires Python (\d+(?:\.\d+)*)"),
                str(newmin),
            ),
        )
        if (self.directory / "docs").exists():
            log.info("Updating docs/index.rst ...")
            map_lines(
                self.directory / "docs" / "index.rst",
                partial(
                    replace_group,
                    re.compile(r"requires Python (\d+(?:\.\d+)*)"),
                    str(newmin),
                ),
            )
        self.update_latest_changelog_section(
            lambda items: drop_pyversion_chlog(dropver, items)
        )

        def edit_pyproject_line(line: str) -> str | None:
            if line == f'    "Programming Language :: Python :: {dropver}",\n':
                return None
            else:
                return replace_group(
                    re.compile(r'^requires-python\s*=\s*"(.+)"$'),
                    self.details.python_requires,
                    line,
                )

        log.info("Updating pyproject.toml ...")
        maybe_map_lines(self.directory / "pyproject.toml", edit_pyproject_line)
        if self.details.has_tests:
            log.info("Updating tox.ini ...")
            map_lines(
                self.directory / "tox.ini",
                partial(
                    replace_group,
                    re.compile(r"^envlist\s*=[ \t]*(.+)$"),
                    partial(rm_py_env, dropver),
                ),
            )
        if self.details.has_ci:

            def edit_test_yml_line(line: str) -> str | None:
                if re.fullmatch(
                    rf"{' ' * 10}- ['\x22]?(?:pypy-)?{re.escape(str(dropver))}"
                    rf"['\x22]?\s*",
                    line,
                ):
                    return None
                else:
                    return replace_group(
                        re.compile(
                            rf"^{' ' * 10}- python-version: (['\x22]?"
                            rf"{re.escape(str(dropver))}['\x22]?)\s*$"
                        ),
                        f"'{newmin}'",  # noqa: B028
                        line,
                    )

            log.info("Updating .github/workflows/test.yml ...")
            maybe_map_lines(
                self.directory / ".github" / "workflows" / "test.yml",
                edit_test_yml_line,
            )

    def begin_dev(self, use_next_version: bool = True, quiet: bool = False) -> None:
        chlog = self.get_changelog()
        if (
            chlog is not None
            and chlog.sections
            and chlog.sections[0].release_date is None
        ):
            if not quiet:
                log.info("Project is already in dev state; not adjusting")
            return
        log.info("Preparing for work on next version ...")
        # Set __version__ to the next version number plus ".dev1"
        old_version = self.details.version
        if use_next_version:
            new_version = next_version(old_version)
            self.set_version(f"{new_version}.dev1")
        else:
            new_version = next_version(old_version, post=True)
            self.set_version(new_version)
        # Add new section to top of CHANGELOGs
        new_sect = ChangelogSection(
            version=f"v{new_version}" if use_next_version else None,
            release_date=None,
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
                    intro=(
                        (
                            f".. currentmodule:: {self.details.import_name}\n"
                            "\n"
                            "Changelog\n"
                            "=========\n"
                            "\n"
                        )
                        if docs
                        else ""
                    ),
                    sections=[
                        new_sect,
                        ChangelogSection(
                            version=f"v{old_version}",
                            release_date=date.today(),
                            content="Initial release",
                        ),
                    ],
                )
            self.set_changelog(chlog, docs=docs)

    def update_latest_changelog_section(
        self, func: Callable[[list[str]], list[str]]
    ) -> None:
        for docs in (False, True):
            if docs:
                if not (self.directory / "docs").exists():
                    continue
                log.info("Updating docs/changelog.rst ...")
            else:
                log.info("Updating CHANGELOG ...")
            chlog = self.get_changelog(docs=docs)
            if chlog is not None and chlog.sections:
                items = chlog.sections[0].get_items()
                new_items = func(items)
                if new_items != items:
                    log.info("No change to content")
                else:
                    chlog.sections[0].set_items(new_items)
                    self.set_changelog(chlog, docs=docs)
            else:
                ### TODO: Error?
                log.warning("Changlog is absent/empty; not updating")


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


def rm_py_env(pyv: PyVersion, envlist: str) -> str:
    envs = envlist.strip().split(",")
    try:
        envs.remove(pyv.pyenv)
    except ValueError:
        pass
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


def drop_pyversion_chlog(dropver: PyVersion, items: list[str]) -> list[str]:
    return support_pyversion_chlog("Drop support for Python", dropver, items)


def add_pyversion_chlog(dropver: PyVersion, items: list[str]) -> list[str]:
    return support_pyversion_chlog("Support Python", dropver, items)


def support_pyversion_chlog(
    prefix: str, newver: PyVersion, items: list[str]
) -> list[str]:
    re_prefix = re.escape(prefix)
    for i, it in enumerate(items):
        if m := re.fullmatch(rf"- {re_prefix} (\d+\.\d+)", it):
            dropped = [m[1]]
        elif m := re.fullmatch(rf"- {re_prefix} (\d+\.\d+) and (\d+\.\d+)", it):
            dropped = [m[1], m[2]]
        elif m := re.fullmatch(
            rf"- {re_prefix} (\d+\.\d+(?:, \d+\.\d+)+), and (\d+\.\d+)",
            it,
        ):
            dropped = [*m[1].split(", "), m[2]]
        else:
            continue
        dropped.append(str(newver))
        dropped.sort(key=PyVersion)
        if len(dropped) == 2:
            ln = f"- {prefix} {dropped[0]} and {dropped[1]}"
        else:
            pre_and = ", ".join(dropped[:-1])
            ln = f"- {prefix} {pre_and}, and {dropped[-1]}"
        items[i] = ln
        return items
    items.append(f"- {prefix} {newver}")
    return items
