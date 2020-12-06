import click
from   ..inspecting import InvalidProjectError
from   ..project    import Project

@click.command()
def cli():
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    project.unflatten()
