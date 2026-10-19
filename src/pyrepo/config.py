from __future__ import annotations
from pathlib import Path
from tomllib import load as toml_load
import click
from .clack import ConfigurableGroup

DEFAULT_CFG = Path.home() / ".config" / "pyrepo.toml"


def configure(
    ctx: click.Context, _param: click.Parameter, filename: str | Path
) -> None:
    try:
        with open(filename, "rb") as fp:
            cfg = toml_load(fp)
    except FileNotFoundError:
        cfg = {}
    opts = cfg.get("options")
    if isinstance(opts, dict):  ### TODO: else: warn? error?
        from .__main__ import main

        assert isinstance(main, ConfigurableGroup)
        ctx.default_map = main.process_config(opts)
