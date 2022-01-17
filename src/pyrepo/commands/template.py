from typing import Optional, Sequence, TextIO
import click
from ..project import Project, with_project
from ..util import cpe_no_tb, get_jinja_env


@click.command()
@click.option("-o", "--outfile", type=click.File("w", encoding="utf-8"))
@click.argument("template", nargs=-1)
@with_project
@cpe_no_tb
def cli(project: Project, template: Sequence[str], outfile: Optional[TextIO]) -> None:
    """Replace files with their re-evaluated templates"""
    jenv = get_jinja_env()
    if outfile is not None:
        if len(template) != 1:
            raise click.UsageError(
                "--outfile may only be used with a single template argument"
            )
        print(project.details.render_template(template[0], jenv), end="", file=outfile)
    else:
        for tmplt in template:
            project.write_template(tmplt, jenv)
