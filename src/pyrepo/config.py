from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import platform
import click
import requests
import tomli
from pyrepo import __url__, __version__
from .clack import ConfigurableGroup
from .gh import GitHub

DEFAULT_CFG = Path.home() / ".config" / "pyrepo.toml"

EXTRA_ACCEPT = ["application/vnd.github.mercy-preview"]  # topics

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
            cfg = tomli.load(fp)
    except FileNotFoundError:
        cfg = {}

    try:
        token = cfg["auth"]["github"]["token"]
    except (KeyError, AttributeError):
        token = None

    ctx.obj = Config(
        gh=GitHub(
            token=token,
            headers={"User-Agent": USER_AGENT},
            extra_accept=EXTRA_ACCEPT,
        ),
    )

    opts = cfg.get("options")
    if isinstance(opts, dict):  ### TODO: else: warn? error?
        from .__main__ import main

        assert isinstance(main, ConfigurableGroup)
        ctx.default_map = main.process_config(opts)
