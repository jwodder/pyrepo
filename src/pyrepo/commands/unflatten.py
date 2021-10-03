import click
from ..project import Project, with_project


@click.command()
@with_project
def cli(project: Project) -> None:
    """Convert a "flat" project to a "non-flat"/"package" project"""
    project.unflatten()
