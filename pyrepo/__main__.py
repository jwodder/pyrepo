import os
import click
from   .        import __version__
from   .config  import DEFAULT_CFG, configure
from   .init    import init
from   .release import release

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    '-c', '--config',
    type         = click.Path(dir_okay=False),
    default      = DEFAULT_CFG,
    show_default = True,
    help         = 'Use the specified configuration file',
)
@click.option(
    '-C', '--chdir',
    type    = click.Path(exists=True, file_okay=False, dir_okay=True),
    help    = 'Change directory before running',
    metavar = 'DIR',
)
@click.version_option(
    __version__, '-V', '--version', message='jwodder-pyrepo %(version)s',
)
@click.pass_context
def main(ctx, chdir, config):
    configure(ctx, config)
    if chdir is not None:
        os.chdir(chdir)

main.add_command(init, 'init')
main.add_command(release, 'release')

if __name__ == '__main__':
    main()
