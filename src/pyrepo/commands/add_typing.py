import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@with_project
@cpe_no_tb
def cli(project: Project) -> None:
    """Add configuration for type annotations and the checking thereof"""
    project.add_typing()
