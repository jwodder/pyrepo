import json
import click
from   ..inspecting import UninitializedProjectError, inspect_project

@click.command()
def cli():
    """ Extract template variables from a project """
    try:
        data = inspect_project()
    except UninitializedProjectError as e:
        raise click.UsageError(str(e))
    click.echo(json.dumps(data, indent=4, sort_keys=True))
