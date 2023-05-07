from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import platform
import sys
import click
import requests
from pyrepo import __url__, __version__
from .clack import ConfigurableGroup
from .gh import GitHub

if sys.version_info[:2] >= (3, 11):
    from tomllib import load as toml_load
else:
    from tomli import load as toml_load

DEFAULT_CFG = Path.home() / ".config" / "pyrepo.toml"

USER_AGENT = "jwodder-pyrepo/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)


@dataclass
class Config:
    gh: GitHub


def configure(
    ctx: click.Context, _param: click.Parameter, filename: str | Path
) -> None:
    try:
        with open(filename, "rb") as fp:
            cfg = toml_load(fp)
    except FileNotFoundError:
        cfg = {}

    try:
        token = cfg["auth"]["github"]["token"]
    except (KeyError, AttributeError):
        token = None

    ctx.obj = Config(gh=GitHub(token=token, headers={"User-Agent": USER_AGENT}))

    opts = cfg.get("options")
    if isinstance(opts, dict):  ### TODO: else: warn? error?
        from .__main__ import main

        assert isinstance(main, ConfigurableGroup)
        ctx.default_map = main.process_config(opts)
