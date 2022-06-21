import json
import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@with_project
@cpe_no_tb
def cli(project: Project) -> None:
    """Extract template variables from a project"""
    click.echo(json.dumps(project.details.for_json(), indent=4, sort_keys=True))
