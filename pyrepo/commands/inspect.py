import json
from   os.path      import exists
from   pathlib      import Path
import click
from   ..inspecting import inspect_project

@click.command()
def cli():
    """ Extract template variables from a project """
    if not (exists('setup.py') and exists('setup.cfg')):
        raise click.UsageError('Project repository has not been initialized')
    click.echo(json.dumps(inspect_project(Path()), indent=4, sort_keys=True))
