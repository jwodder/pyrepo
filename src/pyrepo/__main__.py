from   importlib import import_module
import logging
import os
from   pathlib   import Path
import click
import colorlog
from   .         import __version__
from   .config   import DEFAULT_CFG, configure

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
    """ Manage Python packaging boilerplate """
    configure(ctx, config)
    if chdir is not None:
        os.chdir(chdir)
    colorlog.basicConfig(
        format='%(log_color)s[%(levelname)-8s] %(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'bold',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        },
        level=logging.INFO,
    )

for fpath in Path(__file__).with_name('commands').iterdir():
    modname = fpath.stem
    if modname.isidentifier() and not modname.startswith('_') and \
            (fpath.suffix == '' and (fpath / '__init__.py').exists()
                or fpath.suffix == '.py'):
        submod = import_module('.' + modname, 'pyrepo.commands')
        main.add_command(submod.cli, modname.replace('_', '-'))

if __name__ == '__main__':
    main()
