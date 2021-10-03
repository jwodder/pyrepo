import json
import click
from ..project import Project, with_project


@click.command()
@with_project
def cli(project: Project) -> None:
    """Extract template variables from a project"""
    click.echo(json.dumps(project.get_template_context(), indent=4, sort_keys=True))
