from __future__ import annotations
import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@with_project
@cpe_no_tb
def cli(project: Project) -> None:
    """Drop support for the lowest currently-supported Python version"""
    project.drop_pyversion()
