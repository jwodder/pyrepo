#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "click ~= 8.0",
#     "in-place ~= 1.0",
# ]
# ///

# Migrate from setuptools to hatch:
# - Rewrite `pyproject.toml` to use hatch and include settings from `setup.cfg`
#  - Preserve mypy config
#  - Preserve `[tool.versioningit]` in `pyproject.toml`
# - If the project is a flat module, undo the `src/` layout (including
#   adjusting the references to the `src` directory in `tox.ini`)
# - Configure Dependabot to check for Python dependency updates
# - Delete MANIFEST.in
# - Remove obsolete entries from `.gitignore`
# - Update CHANGELOG.md and docs/changelog.rst, if they exist
# - Commit (unless --no-git given)

from __future__ import annotations
from configparser import ConfigParser
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any
import click
from in_place import InPlace

BOILERPLATE_MYPY_OPTIONS = {
    "allow_incomplete_defs",
    "allow_untyped_defs",
    "ignore_missing_imports",
    "no_implicit_optional",
    "implicit_reexport",
    "local_partial_types",
    "pretty",
    "show_error_codes",
    "show_traceback",
    "strict_equality",
    "warn_redundant_casts",
    "warn_return_any",
    "warn_unreachable",
}


@click.command()
@click.option("--git/--no-git", default=True)
@click.option("--init", is_flag=True, help="Migrate a `pyrepo init` test case")
@click.argument(
    "dirpath",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=os.curdir,
)
def main(dirpath: Path, git: bool, init: bool) -> None:
    migrate_setup(dirpath, init)
    unsrc(dirpath)
    use_dependabot(dirpath)
    log("Deleting MANIFEST.in ...")
    (dirpath / "MANIFEST.in").unlink()
    update_gitignore(dirpath)
    update_changelog(dirpath)
    if git:
        log("Committing ...")
        commit(dirpath, "Switch to Hatch")


def migrate_setup(dirpath: Path, init: bool) -> None:
    log("Migrating from setup.cfg to pyproject.toml ...")
    uses_versioningit = (
        "[tool.versioningit]"
        in (dirpath / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    )
    (root,) = (dirpath / "src").iterdir()
    if root.suffix == ".py":
        import_name = root.stem
        is_flat = True
    else:
        import_name = root.name
        is_flat = False
    cfg = ConfigParser(interpolation=None)
    with (dirpath / "setup.cfg").open(encoding="utf-8") as fp:
        cfg.read_string(fp.read())
    project_name = cfg["metadata"]["name"]
    description = cfg["metadata"]["description"]
    author = cfg["metadata"]["author"]
    author_email = cfg["metadata"]["author_email"]
    keywords = cfg["metadata"].get("keywords", "").strip().splitlines()
    classifiers = cfg["metadata"].get("classifiers", "").strip().splitlines()
    urls: dict[str, str] = {}
    for ln in cfg["metadata"]["project_urls"].strip().splitlines():
        name, _, u = ln.partition(" = ")
        urls[name] = u
    python_requires = cfg["options"]["python_requires"]
    install_requires = [
        req.replace('"', "'")
        for req in cfg["options"].get("install_requires", "").strip().splitlines()
    ]

    extras: dict[str, list[str]] = {}
    if cfg.has_section("options.extras_require"):
        for xtr, deps in cfg["options.extras_require"].items():
            extras[xtr] = deps.strip().splitlines()

    commands: dict[str, str] = {}
    entry_points: dict[str, dict[str, str]] = {}
    if cfg.has_section("options.entry_points"):
        for group, raw_eps in cfg["options.entry_points"].items():
            eps = {}
            for ln in raw_eps.strip().splitlines():
                name, _, value = ln.partition(" = ")
                eps[name] = value
            if group == "console_scripts":
                commands = eps
            else:
                entry_points[group] = eps

    custom_mypy: dict[str, str] = {}
    custom_mypy_sections: dict[str, dict[str, str]] = {}
    pydantic_mypy: dict[str, str] = {}
    if cfg.has_section("mypy"):
        has_mypy = True
        for k, v in cfg["mypy"].items():
            if k not in BOILERPLATE_MYPY_OPTIONS:
                if k == "plugins":
                    plugins = re.split(r"\s*,\s*", v)
                    custom_mypy[k] = "[" + ", ".join(map(qqrepr, plugins)) + "]"
                else:
                    custom_mypy[k] = cfg2toml(v)
        for sectname in cfg.sections():
            if sectname.startswith("mypy-"):
                module = sectname.removeprefix("mypy-")
                custom_mypy_sections[module] = {
                    k: cfg2toml(v) for k, v in cfg[sectname].items()
                }
        if cfg.has_section("pydantic-mypy"):
            for k, v in cfg["pydantic-mypy"].items():
                pydantic_mypy[k] = cfg2toml(v)
    else:
        has_mypy = False

    with (dirpath / "pyproject.toml").open("w", encoding="utf-8") as fp:
        print("[build-system]", file=fp)
        if uses_versioningit:
            print('requires = ["hatchling", "versioningit"]', file=fp)
        else:
            print('requires = ["hatchling"]', file=fp)
        print('build-backend = "hatchling.build"', file=fp)
        print(file=fp)
        print("[project]", file=fp)
        print(f'name = "{project_name}"', file=fp)
        print('dynamic = ["version"]', file=fp)
        print(f'description = "{description}"', file=fp)
        print('readme = "README.rst"', file=fp)
        print(f'requires-python = "{python_requires}"', file=fp)
        print('license = "MIT"', file=fp)
        print('license-files = { paths = ["LICENSE"] }', file=fp)
        print("authors = [", file=fp)
        print(f'    {{ name = "{author}", email = "{author_email}" }}', file=fp)
        print("]", file=fp)
        print(file=fp)
        print("keywords = [", file=fp)
        if init:
            print("    ###", file=fp)
        else:
            for k in keywords:
                print(f'    "{k}",', file=fp)
        print("]", file=fp)
        print(file=fp)
        print("classifiers = [", file=fp)
        if init:
            if classifiers[-1:] == ["Typing :: Typed"]:
                after = [classifiers.pop()]
            else:
                after = []
            for c in classifiers:
                print(f'    "{c}",', file=fp)
            print("    ###", file=fp)
            for c in after:
                print(f'    "{c}",', file=fp)
        else:
            for c in classifiers:
                print(f'    "{c}",', file=fp)
        print("]", file=fp)
        print(file=fp)
        if install_requires:
            print("dependencies = [", file=fp)
            for dep in install_requires:
                print(f'    "{dep}",', file=fp)
            print("]", file=fp)
        else:
            print("dependencies = []", file=fp)

        if extras:
            print(file=fp)
            print("[project.optional-dependencies]", file=fp)
            for xtr, deps in extras.items():
                deplist = ", ".join(f'"{d}"' for d in deps)
                print(f"{xtr} = [{deplist}]", file=fp)

        if commands:
            print(file=fp)
            print("[project.scripts]", file=fp)
            for name, ep in commands.items():
                print(f'{name} = "{ep}"', file=fp)

        for group, eps in entry_points.items():
            print(file=fp)
            print(f'[project.entry-points."{group}"]', file=fp)
            for k, v in eps.items():
                print(f'{k} = "{v}"', file=fp)

        print(file=fp)
        print("[project.urls]", file=fp)
        for label, u in urls.items():
            print(f'"{label}" = "{u}"', file=fp)
        print(file=fp)

        print("[tool.hatch.version]", file=fp)
        if uses_versioningit:
            print('source = "versioningit"', file=fp)
        elif is_flat:
            print(f'path = "{import_name}.py"', file=fp)
        else:
            print(f'path = "src/{import_name}/__init__.py"', file=fp)

        print(file=fp)
        print("[tool.hatch.build.targets.sdist]", file=fp)
        print("include = [", file=fp)
        print('    "/docs",', file=fp)
        if is_flat:
            print(f'    "/{import_name}.py",', file=fp)
        else:
            print('    "/src",', file=fp)
        print('    "/test",', file=fp)
        print('    "CHANGELOG.*",', file=fp)
        print('    "CONTRIBUTORS.*",', file=fp)
        print('    "tox.ini",', file=fp)
        print("]", file=fp)
        print(file=fp)
        print("[tool.hatch.envs.default]", file=fp)
        print('python = "3"', file=fp)

        if has_mypy:
            print(file=fp)
            print("[tool.mypy]", file=fp)
            print("allow_incomplete_defs = false", file=fp)
            print("allow_untyped_defs = false", file=fp)
            print("ignore_missing_imports = false", file=fp)
            print("# <https://github.com/python/mypy/issues/7773>:", file=fp)
            print("no_implicit_optional = true", file=fp)
            print("implicit_reexport = false", file=fp)
            print("local_partial_types = true", file=fp)
            print("pretty = true", file=fp)
            print("show_error_codes = true", file=fp)
            print("show_traceback = true", file=fp)
            print("strict_equality = true", file=fp)
            print("warn_redundant_casts = true", file=fp)
            print("warn_return_any = true", file=fp)
            print("warn_unreachable = true", file=fp)
            for k, v in custom_mypy.items():
                print(f"{k} = {v}", file=fp)
            for module, opts in custom_mypy_sections.items():
                print(file=fp)
                print("[[tool.mypy.overrides]]", file=fp)
                print(f'module = "{module}"', file=fp)
                for k, v in opts.items():
                    print(f"{k} = {v}", file=fp)
            if pydantic_mypy:
                print(file=fp)
                print("[tool.pydantic-mypy]", file=fp)
                for k, v in pydantic_mypy.items():
                    print(f"{k} = {v}", file=fp)

    (dirpath / "setup.cfg").unlink()


def cfg2toml(s: str) -> str:
    if s.lower() in ("true", "false"):
        return s.lower()
    else:
        return f'"{s}"'


def unsrc(dirpath: Path) -> None:
    pys = list((dirpath / "src").glob("*.py"))
    if pys:
        assert len(pys) == 1
        log("Un-src'ing flat module ...")
        (p,) = pys
        module_name = p.name
        p.rename(dirpath / module_name)
        (dirpath / "src").rmdir()
        if (dirpath / "tox.ini").exists():
            log("Updating 'src' references in tox.ini ...")
            with InPlace(dirpath / "tox.ini", encoding="utf-8") as fp:
                for line in fp:
                    if line.strip() == "src_paths = src":
                        continue
                    line = re.sub(
                        r"^(\s+(?:flake8|mypy)\s+)src\b", rf"\1{module_name}", line
                    )
                    if line.rstrip() == "    src":
                        line = f"    {module_name}\n"
                    elif line.rstrip() == "    .tox/**/site-packages":
                        line = line.rstrip() + f"/{module_name}\n"
                    print(line, end="", file=fp)


def use_dependabot(dirpath: Path) -> None:
    if not (dirpath / ".github" / "dependabot.yml").exists():
        return
    log("Updating .github/dependabot.yml ...")
    with InPlace(dirpath / ".github" / "dependabot.yml", encoding="utf-8") as fp:
        for line in fp:
            fp.write(line)
            if line.strip() == "updates:":
                print("  - package-ecosystem: pip", file=fp)
                print("    directory: /", file=fp)
                print("    schedule:", file=fp)
                print("      interval: weekly", file=fp)
                print("    commit-message:", file=fp)
                print('      prefix: "[python]"', file=fp)
                print("    labels:", file=fp)
                print("      - dependencies", file=fp)
                print("      - d:python", file=fp)
                print(file=fp)


def update_gitignore(dirpath: Path) -> None:
    log("Updating .gitignore ...")
    with InPlace(dirpath / ".gitignore", encoding="utf-8") as fp:
        for line in fp:
            if line.strip() in {
                "*.egg",
                "*.egg-info/",
                "*.pyc",
                ".cache/",
                ".eggs/",
                ".pytest_cache/",
                "build/",
                "docs/.doctrees/",
                "venv/",
            }:
                continue
            fp.write(line)


def update_changelog(dirpath: Path) -> None:
    for p in [Path("CHANGELOG.md"), Path("docs", "changelog.rst")]:
        if (dirpath / p).exists():
            state = -1  # -1 = before first section, 0 = in, 1 = after
            log(f"Adding entry to {p} ...")
            with InPlace(dirpath / p, encoding="utf-8") as fp:
                for line in fp:
                    if state < 0 and re.fullmatch(r"-{4,}", line.strip()):
                        state = 0
                    if state == 0 and not line.strip():
                        print("- Migrated from setuptools to hatch", file=fp)
                        state = 1
                    print(line, end="", file=fp)


def commit(dirpath: Path, msg: str) -> None:
    runcmd("git", "add", "-A", cwd=dirpath)
    runcmd("git", "commit", "-m", msg, cwd=dirpath)


def runcmd(*args: str | Path, **kwargs: Any) -> None:
    argstrs = [str(a) for a in args]
    click.secho("+" + shlex.join(argstrs), err=True, fg="green")
    r = subprocess.run(argstrs, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)


def log(msg: str) -> None:
    click.secho(msg, err=True, bold=True)


def qqrepr(s: str) -> str:
    """Produce a repr(string) enclosed in double quotes"""
    return json.dumps(s, ensure_ascii=False)


if __name__ == "__main__":
    main()
