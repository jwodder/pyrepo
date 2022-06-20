from __future__ import annotations
from configparser import ConfigParser
from pathlib import Path
import platform
from typing import Any, Dict
import click
from pydantic import BaseModel
import requests
from pyrepo import __url__, __version__
from .gh import GitHub

DEFAULT_CFG = Path.home() / ".config" / "pyrepo.cfg"

DEFAULTS = {
    "options": {
        "author": "Anonymous",
        "author_email": "USER@HOST",
    },
}

EXTRA_ACCEPT = ["application/vnd.github.mercy-preview"]  # topics

USER_AGENT = "jwodder-pyrepo/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)


class Config(BaseModel):
    defaults: Dict[str, Any]
    gh: GitHub

    class Config:
        arbitrary_types_allowed = True


def configure(ctx: click.Context, filename: str | Path) -> None:
    cfg = ConfigParser(interpolation=None)
    cfg.optionxform = lambda s: s.lower().replace("-", "_")  # type: ignore[assignment]
    cfg.read_dict(DEFAULTS)
    ### TODO: Check the return value and raise an exception if it's empty:
    cfg.read(filename)

    ctx.obj = Config(
        defaults={},
        gh=GitHub(
            token=cfg.get("auth.github", "token", fallback=None),
            headers={"User-Agent": USER_AGENT},
            extra_accept=EXTRA_ACCEPT,
        ),
    )

    from .__main__ import main

    for cmdname, cmdobj in main.commands.items():
        if cfg.has_section(f"options.{cmdname}"):
            defaults: dict[str, Any] = dict(cfg[f"options.{cmdname}"])
            for p in cmdobj.params:
                if isinstance(p, click.Option) and p.is_flag and p.name in defaults:
                    try:
                        defaults[p.name] = cfg.BOOLEAN_STATES[defaults[p.name].lower()]
                    except KeyError:
                        raise click.UsageError(
                            f"Invalid boolean value for config option {p.name}:"
                            f" {defaults[p.name]!r}"
                        )
            ctx.obj.defaults[cmdname] = defaults
