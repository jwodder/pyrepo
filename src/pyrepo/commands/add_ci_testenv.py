import logging
import click
from ..project import Project, with_project
from ..util import cpe_no_tb

log = logging.getLogger(__name__)


@click.command()
@click.argument("testenv")
@click.argument("pyver")
@with_project
@cpe_no_tb
def cli(project: Project, testenv: str, pyver: str) -> None:
    """Add a TESTENV job with the given PYVER to the CI configuration"""
    project.add_ci_testenv(testenv, pyver)
