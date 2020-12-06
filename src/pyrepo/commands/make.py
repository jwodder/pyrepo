import click
from   ..inspecting import InvalidProjectError
from   ..project    import Project

@click.command()
@click.option('-c', '--clean', is_flag=True, default=False)
@click.option('--sdist/--no-sdist', default=True)
@click.option('--wheel/--no-wheel', default=True)
def cli(clean, sdist, wheel):
    """ Build an sdist and/or wheel for a project """
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    project.build(clean=clean, sdist=sdist, wheel=wheel)
