# /// script
# dependencies = [
#     "click ~= 8.0",
#     "jwodder-pyrepo @ git+https://github.com/jwodder/pyrepo@447b4c8",
# ]
# ///

# Replace 'pypy3' Python versions specs in .github/workflows/test.yml with a
# list of appropriate 'pypy-3.X' specs

from pathlib import Path
import re
import subprocess
import sys
import click
from pyrepo.project import Project
from pyrepo.util import map_lines, pypy_supported, runcmd


@click.command()
@click.option("--git/--no-git", default=True)
@click.argument(
    "dirpath", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
def main(dirpath, git):
    project = Project.from_directory(dirpath)
    if not project.supports_pypy3:
        log("Project does not support PyPy; doing nothing")
        return
    if not project.has_ci:
        log("Project does not have CI; doing nothing")
        return
    pypy_versions = pypy_supported(project.python_versions)
    log("Updating .github/workflows/test.yml ...")
    log("pypy3 → " + ", ".join(f"pypy-{v}" for v in pypy_versions))
    modified = False

    def adjust_pypy(line):
        nonlocal modified
        if m := re.fullmatch(r"(\s+)- 'pypy3'\s*", line):
            indent = m[1]
            log("File updated")
            modified = True
            return "".join(f"{indent}- 'pypy-{v}'\n" for v in pypy_versions)
        else:
            return line

    map_lines(project.directory / ".github" / "workflows" / "test.yml", adjust_pypy)
    if not modified:
        log("'pypy3' line not found!")
        sys.exit(1)
    if git:
        runcmd("git", "add", ".github/workflows/test.yml", cwd=dirpath)
        commit(dirpath, "Update PyPy versions in CI")


def commit(dirpath, msg):
    if (
        subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dirpath).returncode
        != 0
    ):
        runcmd("git", "commit", "-m", msg, cwd=dirpath)
    else:
        log("Nothing to commit")


def log(msg):
    click.secho(msg, err=True, bold=True)


if __name__ == "__main__":
    main()
