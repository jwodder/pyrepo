import click
from ..project import Project, with_project


@click.command()
@with_project
def cli(project: Project) -> None:
    """Add configuration for type annotations and the checking thereof"""
    project.add_typing()
