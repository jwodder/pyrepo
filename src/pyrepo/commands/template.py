from typing import Optional, Sequence, TextIO
import click
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@click.option("-o", "--outfile", type=click.File("w", encoding="utf-8"))
@click.argument("template", nargs=-1)
@with_project
@cpe_no_tb
def cli(project: Project, template: Sequence[str], outfile: Optional[TextIO]) -> None:
    """Replace files with their re-evaluated templates"""
    twriter = project.get_template_writer()
    if outfile is not None:
        if len(template) != 1:
            raise click.UsageError(
                "--outfile may only be used with a single template argument"
            )
        print(twriter.render(template[0]), end="", file=outfile)
    else:
        for tmplt in template:
            twriter.write(tmplt)
