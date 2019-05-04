from   pathlib           import Path
import click
from   ..inspect_project import inspect_project
from   ..util            import jinja_env

@click.command()
@click.option('-o', '--outfile', type=click.File('w', encoding='utf-8'))
@click.argument('template', nargs=-1)
def cli(template, outfile):
    """ Replace files with their re-evaluated templates """
    env = inspect_project()
    jenv = jinja_env()
    if outfile is not None:
        if len(template) != 1:
            raise click.UsageError(
                '--outfile may only be used with a single template argument'
            )
        print(jenv.get_template(template[0]+'.j2').render(env).rstrip(),
              file=outfile)
    else:
        for tmplt in template:
            p = Path(tmplt)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                jenv.get_template(tmplt+'.j2').render(env).rstrip() + '\n',
                encoding='utf-8',
            )
