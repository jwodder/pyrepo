import click
from   ..inspecting import InvalidProjectError
from   ..project    import Project
from   ..util       import get_jinja_env

@click.command()
@click.option('-o', '--outfile', type=click.File('w', encoding='utf-8'))
@click.argument('template', nargs=-1)
def cli(template, outfile):
    """ Replace files with their re-evaluated templates """
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    jenv = get_jinja_env()
    if outfile is not None:
        if len(template) != 1:
            raise click.UsageError(
                '--outfile may only be used with a single template argument'
            )
        print(project.render_template(template[0], jenv), end='', file=outfile)
    else:
        for tmplt in template:
            project.write_template(tmplt, jenv)
