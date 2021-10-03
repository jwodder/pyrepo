import click
from ..project import Project, with_project


@click.command()
@click.option(
    "-c",
    "--clean",
    is_flag=True,
    default=False,
    help="Delete dist/ and build/ before building",
)
@click.option(
    "--sdist/--no-sdist",
    default=True,
    help="Whether to build an sdist [default: true]",
)
@click.option(
    "--wheel/--no-wheel",
    default=True,
    help="Whether to build a wheel [default: true]",
)
@with_project
def cli(project: Project, clean: bool, sdist: bool, wheel: bool) -> None:
    """Build an sdist and/or wheel for a project"""
    project.build(clean=clean, sdist=sdist, wheel=wheel)
