import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@with_project
@cpe_no_tb
def cli(project: Project) -> None:
    """Convert a "flat" project to a "non-flat"/"package" project"""
    project.unflatten()
