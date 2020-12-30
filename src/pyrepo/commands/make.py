import click
from   ..inspecting import InvalidProjectError
from   ..project    import Project

@click.command()
@click.option(
    '-c', '--clean',
    is_flag=True,
    default=False,
    help='Delete dist/ and build/ before building',
)
@click.option(
    '--sdist/--no-sdist',
    default=True,
    help='Whether to build an sdist [default: true]',
)
@click.option(
    '--wheel/--no-wheel',
    default=True,
    help='Whether to build a wheel [default: true]',
)
def cli(clean, sdist, wheel):
    """ Build an sdist and/or wheel for a project """
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    project.build(clean=clean, sdist=sdist, wheel=wheel)
