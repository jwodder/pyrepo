from __future__ import annotations
from typing import Any
import click


class ConfigurableCommand(click.Command):
    def __init__(
        self,
        allow_config: list[str] | None = None,
        disallow_config: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.allow_config = allow_config
        self.disallow_config = disallow_config

    def is_configurable(self, paramname: str) -> bool:
        return (self.allow_config is None or paramname in self.allow_config) and (
            self.disallow_config is None or paramname not in self.disallow_config
        )

    def process_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        out_cfg: dict[str, Any] = {}
        params = {p.name for p in self.params}
        for k, v in cfg.items():
            k = k.replace("-", "_")
            if k in params and self.is_configurable(k):
                ### TODO: Enforce type-checking here?
                ### TODO: Handle feature switches (especially ones with
                ###       non-string values, i.e., release's bump options)
                out_cfg[k] = str(v)
        return out_cfg


class ConfigurableGroup(ConfigurableCommand, click.Group):
    def process_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        out_cfg = super().process_config(cfg)
        for cmdname, cmdobj in self.commands.items():
            ### TODO: Warn or error on non-dict values?
            if isinstance(cmdobj, ConfigurableCommand) and isinstance(
                c := cfg.get(cmdname), dict
            ):
                out_cfg[cmdname] = cmdobj.process_config(c)
        return out_cfg
