import click
from   ..inspecting import InvalidProjectError
from   ..project    import Project

@click.command()
def cli():
    """ Add configuration for type annotations and the checking thereof """
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    project.add_typing()
