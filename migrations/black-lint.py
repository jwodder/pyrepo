# Go black:
# - Update tox.ini for post-black flake ignore rules
# - Add .pre-commit-config.yaml
# - If --no-git is not given:
#  - Run "pre-commit install"
#  - Run "pre-commit run -a"
#  - Commit

# Split linting into a separate tox testenv:
# - Update tox.ini and .github/workflow/test.yml to have lint as a separate
#   testenv
# - Commit (unless --no-git given)

# Update mypy version (and commit unless --no-git given)

from pathlib import Path
import re
import subprocess
import sys
import click
from in_place import InPlace


@click.command()
@click.option("--git/--no-git", default=True)
@click.argument(
    "dirpath", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
def main(dirpath, git):
    blacken(dirpath, git)
    separate_lint(dirpath, git)
    update_mypy(dirpath, git)


PRE_COMMIT_CONFIG = """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.0.1
    hooks:
      - id: check-added-large-files
      - id: check-json
      - id: check-toml
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/psf/black
    rev: 21.6b0
    hooks:
      - id: black

  - repo: https://gitlab.com/pycqa/flake8
    rev: 3.9.2
    hooks:
      - id: flake8
        additional_dependencies:
          - flake8-bugbear
          - flake8-builtins
          - flake8-import-order-jwodder
          - flake8-unused-arguments
        exclude: ^test/data
"""


def blacken(dirpath, git):
    if (dirpath / "tox.ini").exists():
        in_ignore = False
        after_select = False
        with InPlace(dirpath / "tox.ini") as fp:
            for line in fp:
                if line.startswith("select ="):
                    after_select = True
                elif after_select:
                    if not line.strip():
                        line = ""
                    after_select = False
                if line.startswith("ignore ="):
                    line = "ignore = B005,E203,E262,E266,E501,I201,W503\n"
                    in_ignore = True
                elif in_ignore:
                    if line.startswith("    "):
                        line = ""
                    else:
                        in_ignore = False
                fp.write(line)
    (dirpath / ".pre-commit-config.yaml").write_text(PRE_COMMIT_CONFIG)
    if git:
        runcmd("pre-commit", "install", cwd=dirpath)
        # No check, in case of long lines etc.:
        subprocess.run(["pre-commit", "run", "-a"])
        runcmd("git", "add", "-u", cwd=dirpath)
        runcmd("git", "add", ".pre-commit-config.yaml", cwd=dirpath)
        commit(dirpath, "Go black")


def separate_lint(dirpath, git):
    if (dirpath / "tox.ini").exists():
        has_flakes = False
        in_testenv = False
        with InPlace(dirpath / "tox.ini") as fp:
            for line in fp:
                if line.startswith("envlist ="):
                    line = line.replace("= ", "= lint,")
                elif line.strip().startswith("flake8"):
                    line = ""
                    has_flakes = True
                elif line == "[testenv]\n":
                    in_testenv = True
                elif in_testenv and not line.strip():
                    if has_flakes:
                        print(file=fp)
                        print("[testenv:lint]", file=fp)
                        print("deps =", file=fp)
                        print("    flake8~=3.7", file=fp)
                        print("    flake8-bugbear", file=fp)
                        print("    flake8-builtins~=1.4", file=fp)
                        print("    flake8-import-order-jwodder", file=fp)
                        print("    flake8-unused-arguments", file=fp)
                        print("commands =", file=fp)
                        print("    flake8 --config=tox.ini src test", file=fp)
                    in_testenv = False
                fp.write(line)
        if git:
            runcmd("git", "add", "tox.ini", cwd=dirpath)
    if (dirpath / ".github" / "workflows" / "test.yml").exists():
        runcmd("pyrepo", "add-ci-testenv", "lint", "3.6", cwd=dirpath)
        if git:
            runcmd("git", "add", ".github/workflows/test.yml", cwd=dirpath)
    if git:
        commit(dirpath, "Split linting into a separate tox testenv")


def update_mypy(dirpath, git):
    if (dirpath / "tox.ini").exists():
        with InPlace(dirpath / "tox.ini") as fp:
            for line in fp:
                fp.write(re.sub(r"^    mypy\s*~=.*", "    mypy~=0.900", line))
        if git:
            runcmd("git", "add", "tox.ini", cwd=dirpath)
            commit(dirpath, "Update mypy version")


def commit(dirpath, msg):
    if runcmd("git", "diff", "--cached", "--exit-code", cwd=dirpath).returncode != 0:
        runcmd("git", "commit", "-m", msg, cwd=dirpath)
    else:
        click.secho("Nothing to commit", err=True, bold=True)


def runcmd(*args, **kwargs):
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
