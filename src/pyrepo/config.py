from __future__ import annotations
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Any
import click
import requests
from pyrepo import __url__, __version__
from .clack import ConfigurableGroup
from .gh import GitHub

DEFAULT_CFG = Path.home() / ".config" / "pyrepo.cfg"

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
    cfg = ConfigParser(interpolation=None)
    ### TODO: Check the return value and raise an exception if it's empty:
    cfg.read(filename)

    ctx.obj = Config(
        gh=GitHub(
            token=cfg.get("auth.github", "token", fallback=None),
            headers={"User-Agent": USER_AGENT},
            extra_accept=EXTRA_ACCEPT,
        ),
    )

    defaults: dict[str, Any] = {}
    for k, v in cfg.items():
        if k == "options":
            defaults.update(v)
        elif k.startswith("options."):
            defaults[k[8:]] = dict(v)

    from .__main__ import main

    assert isinstance(main, ConfigurableGroup)
    ctx.default_map = main.process_config(defaults)
