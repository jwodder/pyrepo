from typing import Sequence
import click
from ..project import Project, with_project
from ..util import PyVersion, cpe_no_tb


@click.command()
@click.argument("pyversions", type=PyVersion.parse, nargs=-1)
@with_project
@cpe_no_tb
def cli(project: Project, pyversions: Sequence[str]) -> None:
    """Declare support for a given Python version"""
    for v in pyversions:
        project.add_pyversion(v)
