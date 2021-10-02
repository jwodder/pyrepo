from typing import Sequence
import click
from ..inspecting import InvalidProjectError
from ..project import Project
from ..util import PyVersion


@click.command()
@click.argument("pyversions", type=PyVersion.parse, nargs=-1)
def cli(pyversions: Sequence[str]) -> None:
    """Declare support for a given Python version"""
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    for v in pyversions:
        project.add_pyversion(v)
