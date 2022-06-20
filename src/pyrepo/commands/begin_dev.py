import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@click.option(
    "-N",
    "--no-next-version",
    is_flag=True,
    help="Do not calculate a next version for the project",
)
@with_project
@cpe_no_tb
def cli(project: Project, no_next_version: bool) -> None:
    """Begin work on the next version of the project"""
    project.begin_dev(not no_next_version)
