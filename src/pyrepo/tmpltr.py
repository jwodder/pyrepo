from __future__ import annotations
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Optional
from jinja2 import Environment
from .util import get_jinja_env

log = logging.getLogger(__name__)


@dataclass
class Templater:
    jinja_env: Environment = field(init=False, default_factory=get_jinja_env)
    context: dict[str, Any]

    def render(self, template_path: str) -> str:
        return (
            self.jinja_env.get_template(template_path + ".j2")
            .render(self.context)
            .rstrip()
            + "\n"
        )

    def get_template_block(
        self,
        template_name: str,
        block_name: str,
        vars: Optional[dict[str, Any]] = None,
    ) -> str:
        tmpl = self.jinja_env.get_template(template_name)
        context = tmpl.new_context(vars=vars)
        return "".join(tmpl.blocks[block_name](context))


@dataclass
class TemplateWriter(Templater):
    basedir: Path

    def write(self, template_path: str, force: bool = True) -> None:
        outpath = self.basedir / template_path
        if not force and outpath.exists():
            log.info("File %s already exists; not templating", template_path)
            return
        log.info("Writing %s ...", template_path)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text(self.render(template_path), encoding="utf-8")
