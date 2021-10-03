import logging
import click
from ..project import Project, with_project
from ..util import cpe_no_tb, get_jinja_env

log = logging.getLogger(__name__)


@click.command()
@click.argument("testenv")
@click.argument("pyver")
@with_project
@cpe_no_tb
def cli(project: Project, testenv: str, pyver: str) -> None:
    """Add a TESTENV job with the given PYVER to the CI configuration"""
    log.info("Adding testenv %r with Python version %r", testenv, pyver)
    project.extra_testenvs[testenv] = pyver
    project.write_template(".github/workflows/test.yml", get_jinja_env())
