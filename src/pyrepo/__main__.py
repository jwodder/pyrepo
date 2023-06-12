from importlib import import_module
import logging
import os
from pathlib import Path
import sys
from typing import Optional
import click
from click_loglevel import LogLevel
import colorlog
from . import __version__
from .clack import ConfigurableGroup
from .config import DEFAULT_CFG, configure


@click.group(
    cls=ConfigurableGroup,
    allow_config=["log_level"],
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "-c",
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CFG,
    show_default=True,
    help="Use the specified configuration file",
    callback=configure,
    is_eager=True,
    expose_value=False,
)
@click.option(
    "-C",
    "--chdir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Change directory before running",
    metavar="DIR",
)
@click.option(
    "-l",
    "--log-level",
    type=LogLevel(),
    default=logging.INFO,
    help="Set logging level  [default: INFO]",
)
@click.version_option(
    __version__,
    "-V",
    "--version",
    message="jwodder-pyrepo %(version)s",
)
def main(chdir: Optional[Path], log_level: int) -> None:
    """Manage Python packaging boilerplate"""
    if chdir is not None:
        os.chdir(chdir)
    colorlog.basicConfig(
        format="%(log_color)s[%(levelname)-8s] %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "bold",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
        level=log_level,
        stream=sys.stderr,
    )


for fpath in Path(__file__).with_name("commands").iterdir():
    modname = fpath.stem
    if (
        modname.isidentifier()
        and not modname.startswith("_")
        and (
            fpath.suffix == ""
            and (fpath / "__init__.py").exists()
            or fpath.suffix == ".py"
        )
    ):
        submod = import_module(f".{modname}", "pyrepo.commands")
        main.add_command(
            submod.cli,  # type: ignore[attr-defined]
            modname.replace("_", "-"),
        )

if __name__ == "__main__":
    main()
