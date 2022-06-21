from __future__ import annotations
import ast
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, List, Optional
from intspan import intspan
from read_version import read_version
from setuptools.config.setupcfg import read_configuration
import versioningit
import yaml
from . import git  # Import module to keep mocking easy
from .readme import Readme
from .util import JSONable, PyVersion, sort_specifier, yield_lines


class InvalidProjectError(Exception):
    pass


def inspect_project(dirpath: str | Path | None = None) -> dict:
    """Fetch various information about an already-initialized project"""
    if dirpath is None:
        directory = Path()
    else:
        directory = Path(dirpath)

    def exists(*fname: str) -> bool:
        return Path(directory, *fname).exists()

    if not exists("pyproject.toml"):
        raise InvalidProjectError("Project is missing pyproject.toml file")
    if not exists("setup.cfg"):
        raise InvalidProjectError("Project is missing setup.cfg file")
    if not exists("src"):
        raise InvalidProjectError("Project does not have src/ layout")

    cfg = read_configuration(directory / "setup.cfg")
    env = {
        "name": cfg["metadata"]["name"],
        "short_description": cfg["metadata"]["description"],
        "author": cfg["metadata"]["author"],
        "author_email": cfg["metadata"]["author_email"],
        "python_requires": sort_specifier(cfg["options"]["python_requires"]),
        "install_requires": cfg["options"].get("install_requires", []),
        # Until <https://github.com/pypa/setuptools/issues/2575> is fixed, we
        # have to determine versions via read_version() instead of
        # read_configuration().
        # "version": cfg["metadata"].get("version"),
        "keywords": cfg["metadata"].get("keywords", []),
        "classifiers": cfg["metadata"].get("classifiers", []),
        "supports_pypy": False,
        "default_branch": git.Git(dirpath=directory).get_default_branch(),
    }

    # if env["version"] is None:
    #    raise InvalidProjectError("Cannot determine project version")

    if cfg["options"].get("packages"):
        env["is_flat_module"] = False
        env["import_name"] = cfg["options"]["packages"][0]
        initfile = directory / "src" / env["import_name"] / "__init__.py"
    else:
        env["is_flat_module"] = True
        env["import_name"] = cfg["options"]["py_modules"][0]
        initfile = directory / "src" / f"{env['import_name']}.py"

    try:
        env["version"] = versioningit.get_version(directory)
        env["uses_versioningit"] = True
    except versioningit.NotVersioningitError:
        env["version"] = read_version(initfile.resolve())
        env["uses_versioningit"] = False

    env["python_versions"] = []
    for clsfr in env["classifiers"]:
        if m := re.fullmatch(r"Programming Language :: Python :: (\d+\.\d+)", clsfr):
            env["python_versions"].append(PyVersion.parse(m[1]))
        if clsfr == "Programming Language :: Python :: Implementation :: PyPy":
            env["supports_pypy"] = True

    env["commands"] = {}
    try:
        commands = cfg["options"]["entry_points"]["console_scripts"]
    except KeyError:
        pass
    else:
        for cmd in commands:
            k, v = re.split(r"\s*=\s*", cmd, maxsplit=1)
            env["commands"][k] = v

    m = re.fullmatch(
        r"https://github.com/([^/]+)/([^/]+)",
        cfg["metadata"]["url"],
    )
    assert m, "Project URL is not a GitHub URL"
    env["github_user"] = m[1]
    env["repo_name"] = m[2]

    if "Documentation" in cfg["metadata"]["project_urls"]:
        m = re.fullmatch(
            r"https?://([-a-zA-Z0-9]+)\.(?:readthedocs|rtfd)\.io",
            cfg["metadata"]["project_urls"]["Documentation"],
        )
        assert m, "Documentation URL is not a Read the Docs URL"
        env["rtfd_name"] = m[1]
    else:
        env["rtfd_name"] = env["name"]

    toxcfg = ConfigParser(interpolation=None)
    toxcfg.read(directory / "tox.ini")  # No-op when tox.ini doesn't exist
    env["has_tests"] = toxcfg.has_section("testenv")

    env["has_doctests"] = False
    for pyfile in (directory / "src").rglob("*.py"):
        if re.search(r"^\s*>>>\s+", pyfile.read_text(), flags=re.M):
            env["has_doctests"] = True
            break

    env["has_typing"] = exists("src", env["import_name"], "py.typed")
    env["has_ci"] = exists(".github", "workflows", "test.yml")
    env["has_docs"] = exists("docs", "index.rst")

    env["codecov_user"] = env["github_user"]
    try:
        with (directory / "README.rst").open(encoding="utf-8") as fp:
            rdme = Readme.load(fp)
    except FileNotFoundError:
        env["has_pypi"] = False
    else:
        for badge in rdme.badges:
            if m := re.fullmatch(
                r"https://codecov\.io/gh/([^/]+)/[^/]+/branch/.+" r"/graph/badge\.svg",
                badge.href,
            ):
                env["codecov_user"] = m[1]
        env["has_pypi"] = any(link["label"] == "PyPI" for link in rdme.header_links)

    with (directory / "LICENSE").open(encoding="utf-8") as fp:
        for line in fp:
            if m := re.match(r"^Copyright \(c\) (\d[-,\d\s]+\d) \w+", line):
                env["copyright_years"] = list(intspan(m[1]))
                break
        else:
            raise InvalidProjectError("Copyright years not found in LICENSE")

    env["extra_testenvs"] = parse_extra_testenvs(
        directory / ".github" / "workflows" / "test.yml"
    )

    return env


@dataclass
class ModuleInfo:
    import_name: str
    is_flat_module: bool
    src_layout: bool


def find_module(dirpath: Path) -> ModuleInfo:
    results: list[ModuleInfo] = []
    if (dirpath / "src").exists():
        dirpath /= "src"
        src_layout = True
    else:
        src_layout = False
    for flat in dirpath.glob("*.py"):
        name = flat.stem
        if name.isidentifier() and name != "setup":
            results.append(
                ModuleInfo(
                    import_name=name,
                    is_flat_module=True,
                    src_layout=src_layout,
                )
            )
    for pkg in dirpath.glob("*/__init__.py"):
        name = pkg.parent.name
        if name.isidentifier():
            results.append(
                ModuleInfo(
                    import_name=name,
                    is_flat_module=False,
                    src_layout=src_layout,
                )
            )
    if len(results) > 1:
        raise InvalidProjectError("Multiple Python modules in repository")
    elif not results:
        raise InvalidProjectError("No Python modules in repository")
    else:
        return results[0]


@dataclass
class Requirements(JSONable):
    python_requires: Optional[str] = None
    requires: Optional[List[str]] = None


def extract_requires(filename: Path) -> Requirements:
    ### TODO: Split off the destructive functionality so that this can be run
    ### idempotently/in a read-only manner
    variables: dict[str, Any] = {
        "python_requires": None,
        "requires": None,
    }
    field_map = {
        "__python_requires__": "python_requires",
        "__requires__": "requires",
    }
    src = filename.read_bytes()
    lines = src.splitlines(keepends=True)
    dellines: list[slice] = []
    tree = ast.parse(src)
    for i, node in enumerate(tree.body):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in field_map
        ):
            variables[field_map[node.targets[0].id]] = ast.literal_eval(node.value)
            if i + 1 < len(tree.body):
                dellines.append(slice(node.lineno - 1, tree.body[i + 1].lineno - 1))
            else:
                dellines.append(slice(node.lineno - 1))
    for sl in reversed(dellines):
        del lines[sl]
    with filename.open("wb") as fp:
        fp.writelines(lines)
    return Requirements.parse_obj(variables)


def parse_requirements(filepath: Path) -> Requirements:
    reqs = Requirements()
    try:
        with filepath.open(encoding="utf-8") as fp:
            for line in fp:
                if m := re.fullmatch(
                    r"\s*#\s*python\s*((?:[=<>!~]=|[<>]|===)\s*\S(?:.*\S)?)\s*",
                    line,
                    flags=re.I,
                ):
                    reqs.python_requires = m[1]
                    break
            fp.seek(0)
            reqs.requires = list(yield_lines(fp))
    except FileNotFoundError:
        pass
    return reqs


def parse_extra_testenvs(filepath: Path) -> dict[str, str]:
    try:
        with filepath.open(encoding="utf-8") as fp:
            workflow = yaml.safe_load(fp)
    except FileNotFoundError:
        return {}
    includes = workflow["jobs"]["test"]["strategy"]["matrix"].get("include", [])
    return {inc["toxenv"]: inc["python-version"] for inc in includes}


def find_project_root(dirpath: Optional[Path] = None) -> Optional[Path]:
    if dirpath is None:
        dirpath = Path()
    for d in (dirpath, *dirpath.resolve().parents):
        if (d / "pyproject.toml").exists():
            return d
    return None
