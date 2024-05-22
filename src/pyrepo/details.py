from __future__ import annotations
from configparser import ConfigParser
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from intspan import intspan
from packaging.specifiers import SpecifierSet
from . import git  # Import module to keep mocking easy
from .inspecting import InvalidProjectError, parse_extra_testenvs
from .readme import Readme
from .tmpltr import Templater
from .util import JSONable, PyVersion, readcmd, sort_specifier

if sys.version_info[:2] >= (3, 11):
    from tomllib import load as toml_load
else:
    from tomli import load as toml_load


@dataclass
class ProjectDetails(JSONable):
    #: The name of the project as it is/will be known on PyPI
    name: str

    version: str
    short_description: str
    author: str
    author_email: str
    install_requires: list[str]
    keywords: list[str]
    classifiers: list[str]
    supports_pypy: bool

    #: Extra testenvs to include runs for in CI, as a mapping from testenv name
    #: to Python version
    extra_testenvs: dict[str, str]

    is_flat_module: bool
    import_name: str
    uses_versioningit: bool

    #: Sorted list of supported Python versions
    python_versions: list[PyVersion]

    python_requires: str

    #: Mapping from command (`console_scripts`) names to entry point
    #: specifications
    commands: dict[str, str]

    github_user: str
    repo_name: str
    rtfd_name: str
    has_tests: bool
    has_typing: bool
    has_doctests: bool
    has_docs: bool
    has_ci: bool
    has_pypi: bool
    copyright_years: list[int]
    default_branch: str

    def __post_init__(self) -> None:
        self.python_versions.sort()

    @classmethod
    def inspect(cls, dirpath: str | Path | None = None) -> ProjectDetails:
        """Fetch various information about an already-initialized project"""
        if dirpath is None:
            directory = Path()
        else:
            directory = Path(dirpath)

        def exists(*fname: str) -> bool:
            return Path(directory, *fname).exists()

        try:
            with (directory / "pyproject.toml").open("rb") as bf:
                pyproj = toml_load(bf)
        except FileNotFoundError:
            raise InvalidProjectError("Project is missing pyproject.toml file")

        metadata = json.loads(
            readcmd(sys.executable, "-m", "hatch", "project", "metadata", cwd=dirpath)
        )

        # `hatch project metadata` normalizes the name, so get it directly from
        # the source
        project_name = pyproj["project"]["name"]

        # `hatch project metadata` sorts classifiers, so get them directly from
        # the source instead to preserve order:
        classifiers = pyproj["project"].get("classifiers", [])

        try:
            version_source = pyproj["tool"]["hatch"]["version"]["source"]
        except (AttributeError, LookupError, TypeError):
            uses_versioningit = False
        else:
            uses_versioningit = version_source == "versioningit"

        if (directory / "src").exists():
            is_flat_module = False
            (pkg,) = (directory / "src").iterdir()
            import_name = pkg.name
        else:
            is_flat_module = True
            (module,) = directory.glob("*.py")
            import_name = module.stem

        python_versions = []
        supports_pypy = False
        for clsfr in classifiers:
            if m := re.fullmatch(
                r"Programming Language :: Python :: (\d+\.\d+)", clsfr
            ):
                python_versions.append(PyVersion.parse(m[1]))
            if clsfr == "Programming Language :: Python :: Implementation :: PyPy":
                supports_pypy = True

        commands = metadata.get("scripts", {})

        m = re.fullmatch(
            r"https://github.com/([^/]+)/([^/]+)",
            metadata["urls"]["Source Code"],
        )
        assert m, "Project URL is not a GitHub URL"
        github_user = m[1]
        repo_name = m[2]

        if "Documentation" in metadata["urls"]:
            m = re.fullmatch(
                r"https?://([-a-zA-Z0-9]+)\.(?:readthedocs|rtfd)\.io",
                metadata["urls"]["Documentation"],
            )
            assert m, "Documentation URL is not a Read the Docs URL"
            rtfd_name = m[1]
        else:
            rtfd_name = project_name

        toxcfg = ConfigParser(interpolation=None)
        toxcfg.read(directory / "tox.ini")  # No-op when tox.ini doesn't exist
        has_tests = toxcfg.has_section("testenv")

        has_doctests = False
        if is_flat_module:
            pyfiles = [directory / f"{import_name}.py"]
        else:
            pyfiles = list((directory / "src").rglob("*.py"))
        has_doctests = any(
            re.search(r"^\s*>>>\s+", p.read_text(encoding="utf-8"), flags=re.M)
            for p in pyfiles
        )

        has_typing = exists("src", import_name, "py.typed")
        has_ci = exists(".github", "workflows", "test.yml")
        has_docs = exists("docs", "index.rst")

        try:
            with (directory / "README.rst").open(encoding="utf-8") as fp:
                rdme = Readme.load(fp)
        except FileNotFoundError:
            has_pypi = False
        else:
            has_pypi = any(link["label"] == "PyPI" for link in rdme.header_links)

        with (directory / "LICENSE").open(encoding="utf-8") as fp:
            for line in fp:
                if m := re.match(r"^Copyright \(c\) (\d[-,\d\s]+\d) \w+", line):
                    copyright_years = list(intspan(m[1]))
                    break
            else:
                raise InvalidProjectError("Copyright years not found in LICENSE")

        extra_testenvs = parse_extra_testenvs(
            directory / ".github" / "workflows" / "test.yml"
        )

        return cls(
            name=project_name,
            short_description=metadata["description"],
            author=metadata["authors"][0]["name"],
            author_email=metadata["authors"][0]["email"],
            python_requires=sort_specifier(SpecifierSet(metadata["requires-python"])),
            install_requires=metadata.get("dependencies", []),
            version=metadata["version"],
            keywords=metadata.get("keywords", []),
            classifiers=classifiers,
            python_versions=python_versions,
            supports_pypy=supports_pypy,
            default_branch=git.Git(dirpath=directory).get_default_branch(),
            uses_versioningit=uses_versioningit,
            is_flat_module=is_flat_module,
            import_name=import_name,
            commands=commands,
            github_user=github_user,
            repo_name=repo_name,
            rtfd_name=rtfd_name,
            has_tests=has_tests,
            has_doctests=has_doctests,
            has_typing=has_typing,
            has_ci=has_ci,
            has_docs=has_docs,
            has_pypi=has_pypi,
            copyright_years=copyright_years,
            extra_testenvs=extra_testenvs,
        )

    def get_templater(self) -> Templater:
        return Templater(context=self.for_json())
