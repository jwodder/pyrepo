from   contextlib  import suppress
import logging
from   pathlib     import Path
import re
from   shutil      import rmtree
import sys
from   typing      import Dict, List, Optional
import attr
from   in_place    import InPlace
from   .changelog  import Changelog
from   .inspecting import inspect_project
from   .util       import runcmd

log = logging.getLogger(__name__)

CHANGELOG_NAMES = ('CHANGELOG.md', 'CHANGELOG.rst')

@attr.s(auto_attribs=True)
class Project:
    directory: Path
    name: str
    version: str
    short_description: str
    author: str
    author_email: str
    python_requires: str
    install_requires: List[str]
    keywords: List[str]
    supports_pypy3: bool
    extra_testenvs: Dict[str,str]
    is_flat_module: bool
    import_name: str
    python_versions: List[str]
    commands: Dict[str, str]
    github_user: str
    codecov_user: str
    repo_name: str
    rtfd_name: str
    has_tests: bool
    has_doctests: bool
    has_docs: bool
    has_ci: bool
    has_pypi: bool
    copyright_years: List[int]

    @classmethod
    def from_directory(cls, dirpath=None):
        if dirpath is None:
            directory = Path()
        else:
            directory = Path(dirpath)
        return cls.from_inspection(directory, inspect_project(directory))

    @classmethod
    def from_inspection(cls, directory, context):
        context = context.copy()
        context["name"] = context.pop("project_name")
        return cls(directory=directory.resolve(), **context)

    @property
    def initfile(self):
        if self.is_flat_module:
            return self.directory / "src" / (self.import_name + ".py")
        else:
            return self.directory / "src" / self.import_name / "__init__.py"

    def get_template_context(self):
        context = attr.asdict(self)
        context.pop("directory")
        context["project_name"] = context.pop("name")
        return context

    def render_template(self, template_path, jinja_env):
        return jinja_env.get_template(template_path + ".j2").render(
            self.get_template_context()
        ).rstrip() + "\n"

    def write_template(self, template_path, jinja_env, force=True):
        outpath = self.directory / template_path
        if not force and outpath.exists():
            return
        log.info("Writing %s ...", template_path)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(
            self.render_template(template_path, jinja_env),
            encoding="utf-8",
        )

    def set_version(self, version):
        log.info('Setting __version__ to %r ...', version)
        with InPlace(self.initfile, mode='t', encoding='utf-8') as fp:
            for line in fp:
                m = re.match(r'^__version__\s*=', line)
                if m:
                    line = m.group(0) + ' ' + repr(version) + '\n'
                print(line, file=fp, end='')
        self.version = version

    def get_changelog(self, docs: bool = False) -> Optional[Changelog]:
        if docs:
            paths = [Path('docs', 'changelog.rst')]
        else:
            paths = CHANGELOG_NAMES
        for p in paths:
            try:
                with (self.directory / p).open(encoding='utf-8') as fp:
                    return Changelog.load(fp)
            except FileNotFoundError:
                continue
        return None

    def set_changelog(self, value: Optional[Changelog], docs: bool = False) \
            -> None:
        if docs:
            paths = [Path('docs', 'changelog.rst')]
        else:
            paths = CHANGELOG_NAMES
        for p in paths:
            fpath = self.directory / p
            if fpath.exists():
                if value is None:
                    fpath.unlink()
                else:
                    with fpath.open('w', encoding='utf-8') as fp:
                        value.save(fp)
                return
        if value is not None:
            fpath = self.directory / paths[0]
            with fpath.open('w', encoding='utf-8') as fp:
                value.save(fp)

    def build(self, sdist=True, wheel=True, clean=False):
        if clean:
            with suppress(FileNotFoundError):
                rmtree(self.directory / 'build')
            with suppress(FileNotFoundError):
                rmtree(self.directory / 'dist')
        if sdist or wheel:
            args = []
            if sdist:
                args.append('--sdist')
            if wheel:
                args.append('--wheel')
            runcmd(sys.executable, '-m', 'build', *args, self.directory)
