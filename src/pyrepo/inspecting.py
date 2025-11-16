from __future__ import annotations
import ast
from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any
from ruamel.yaml import YAML
from .util import yield_lines


class InvalidProjectError(Exception):
    pass


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
        if name.isidentifier():
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
class Requirements:
    python_requires: str | None = None
    requires: list[str] | None = None

    def for_json(self) -> dict[str, Any]:
        return asdict(self)


def extract_requires(filename: Path) -> Requirements:
    ### TODO: Split off the destructive functionality so that this can be run
    ### idempotently/in a read-only manner
    python_requires: str | None = None
    requires: list[str] | None = None
    src = filename.read_bytes()
    lines = src.splitlines(keepends=True)
    dellines: list[slice] = []
    tree = ast.parse(src)
    for i, node in enumerate(tree.body):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            match node.targets[0].id:
                case "__python_requires__":
                    value = ast.literal_eval(node.value)
                    assert isinstance(value, str)
                    python_requires = value
                case "__requires__":
                    value = ast.literal_eval(node.value)
                    assert isinstance(value, list)
                    assert all(isinstance(v, str) for v in value)
                    requires = value
                case _:
                    continue
            if i + 1 < len(tree.body):
                dellines.append(slice(node.lineno - 1, tree.body[i + 1].lineno - 1))
            else:
                dellines.append(slice(node.lineno - 1))
    for sl in reversed(dellines):
        del lines[sl]
    with filename.open("wb") as fp:
        fp.writelines(lines)
    return Requirements(python_requires=python_requires, requires=requires)


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
            workflow = YAML(typ="safe").load(fp)
    except FileNotFoundError:
        return {}
    includes = workflow["jobs"]["test"]["strategy"]["matrix"].get("include", [])
    return {inc["toxenv"]: inc["python-version"] for inc in includes}


def find_project_root(dirpath: Path | None = None) -> Path | None:
    if dirpath is None:
        dirpath = Path()
    for d in (dirpath, *dirpath.resolve().parents):
        if (d / "pyproject.toml").exists():
            return d
    return None
