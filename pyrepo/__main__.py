import os
import click
from   .        import __version__
from   .init    import init
from   .release import release

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    '-C', '--chdir',
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help='Change directory before running',
    metavar='DIR',
)
@click.version_option(
    __version__, '-V', '--version', message='%(prog)s %(version)s',
)
def main(chdir):
    if chdir is not None:
        os.chdir(chdir)

main.add_command(init, 'init')
main.add_command(release, 'release')

if __name__ == '__main__':
    main()
