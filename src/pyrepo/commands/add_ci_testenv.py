import logging
import click
from ..inspecting import InvalidProjectError
from ..project import Project
from ..util import get_jinja_env

log = logging.getLogger(__name__)


@click.command()
@click.argument("testenv")
@click.argument("pyver")
def cli(testenv: str, pyver: str) -> None:
    """Add a TESTENV job with the given PYVER to the CI configuration"""
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    log.info("Adding testenv %r with Python version %r", testenv, pyver)
    project.extra_testenvs[testenv] = pyver
    project.write_template(".github/workflows/test.yml", get_jinja_env())
