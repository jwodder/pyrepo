# isort:
# - Add section to .pre-commit-config.yaml
# - Remove flake8-import-order-jwodder from .pre-commit-config.yaml
# - If tox.ini exists:
#  - Remove flake8-import-order from lint testenv
#  - Remove application-import-names and import-order-style from [flake8]
#  - Add [isort] section
#   - If application-import-names had more than one item, include a
#     known_first_party section
# - If tox.ini does not exist, create it with [flake8] and [isort] sections
# - If --no-git is not given:
#  - Run "pre-commit run -a"
#  - Commit

__requires__ = ["click ~= 8.0", "in_place ~= 0.5", "linesep ~= 0.3"]

from pathlib import Path
import re
import subprocess
import sys
import click
from in_place import InPlace
from linesep import read_paragraphs


@click.command()
@click.option("--git/--no-git", default=True)
@click.argument(
    "dirpath", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
def main(dirpath, git):
    isort(dirpath, git)


PRE_COMMIT_ISORT = """\
  - repo: https://github.com/PyCQA/isort
    rev: 5.9.1
    hooks:
      - id: isort

"""

FLAKE8_CFG = """\
[flake8]
doctests = True
exclude = .*/,build/,dist/,test/data,venv/
hang-closing = False
max-doc-length = 80
max-line-length = 80
unused-arguments-ignore-stub-functions = True
select = C,B,B902,B950,E,E242,F,I,U100,W
ignore = B005,E203,E262,E266,E501,I201,W503
"""

ISORT_CFG = """\
[isort]
atomic = True
force_sort_within_sections = True
honor_noqa = True
lines_between_sections = 0
profile = black
reverse_relative = True
sort_relative_in_force_sorted_sections = True
src_paths = src
"""


def isort(dirpath, git):
    log("Adding isort to .pre-commit-config.yaml ...")
    with InPlace(dirpath / ".pre-commit-config.yaml") as fp:
        for para in read_paragraphs(fp):
            fp.write(
                re.sub(r"^\s*- flake8-import-order-jwodder\n", "", para, flags=re.M)
            )
            if "https://github.com/psf/black" in para:
                fp.write(PRE_COMMIT_ISORT)
    toxpath = dirpath / "tox.ini"
    if toxpath.exists():
        log("Adding [isort] to tox.ini ...")
        with InPlace(toxpath) as fp:
            in_flake8 = False
            known_first_party = None
            for line in fp:
                if line.strip() == "flake8-import-order-jwodder":
                    continue
                if line.strip() == "import-order-style = jwodder":
                    continue
                if m := re.fullmatch(
                    r"application-import-names = \w+(?:,([\w,]+))?", line.strip()
                ):
                    known_first_party = m[1]
                    continue
                if line.strip() == "[flake8]":
                    in_flake8 = True
                elif in_flake8 and line.startswith("["):
                    insertion = ISORT_CFG + "\n"
                    if known_first_party:
                        insertion = re.sub(
                            r"^(?=lines_between_sections)",
                            f"known_first_party = {known_first_party}\n",
                            insertion,
                            flags=re.M,
                        )
                    fp.write(insertion)
                    in_flake8 = False
                fp.write(line)
            if in_flake8:
                insertion = "\n" + ISORT_CFG
                if known_first_party:
                    insertion = re.sub(
                        r"^(?=lines_between_sections)",
                        f"known_first_party = {known_first_party}\n",
                        insertion,
                        flags=re.M,
                    )
                fp.write(insertion)
    else:
        log("Creating tox.ini ...")
        toxpath.write_text(FLAKE8_CFG + "\n" + ISORT_CFG)
    if git:
        # No check, as it fails when isort modifies:
        subprocess.run(["pre-commit", "run", "-a"], cwd=dirpath)
        runcmd("git", "add", "-u", cwd=dirpath)
        runcmd("git", "add", "tox.ini", cwd=dirpath)
        commit(dirpath, "Switch to isort for ordering imports")


def commit(dirpath, msg):
    if (
        subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dirpath).returncode
        != 0
    ):
        runcmd("git", "commit", "-m", msg, cwd=dirpath)
    else:
        log("Nothing to commit")


def runcmd(*args, **kwargs):
    click.secho("+" + " ".join(args), err=True, fg="green")
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)


def log(msg):
    click.secho(msg, err=True, bold=True)


if __name__ == "__main__":
    main()
