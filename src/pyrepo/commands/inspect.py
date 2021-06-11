import json
import click
from ..inspecting import InvalidProjectError, inspect_project


@click.command()
def cli():
    """Extract template variables from a project"""
    try:
        data = inspect_project()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    click.echo(json.dumps(data, indent=4, sort_keys=True))
