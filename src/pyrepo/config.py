from configparser import ConfigParser
from pathlib import Path
import platform
from typing import Any, Dict, List, Union
import click
from pydantic import BaseModel
from pyversion_info import get_pyversion_info
import requests
from pyrepo import __url__, __version__
from .gh import GitHub
from .util import PyVersion

DEFAULT_CFG = str(Path.home() / ".config" / "pyrepo.cfg")

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

MAJOR_PYTHON_VERSIONS = [3]
PYVER_TEMPLATE = '"3.X"'


class Config(BaseModel):
    defaults: Dict[str, Any]
    pyversions: List[PyVersion]
    gh: GitHub

    class Config:
        arbitrary_types_allowed = True


def configure(ctx: click.Context, filename: Union[str, Path]) -> None:
    cfg = ConfigParser(interpolation=None)
    cfg.optionxform = lambda s: s.lower().replace("-", "_")  # type: ignore[assignment]
    cfg.read_dict(DEFAULTS)
    ### TODO: Check the return value and raise an exception if it's empty:
    cfg.read(filename)

    pyvinfo = get_pyversion_info()
    supported_series = [
        v
        for m in map(str, MAJOR_PYTHON_VERSIONS)
        for v in pyvinfo.subversions(m)
        if pyvinfo.is_supported(v)
    ]

    try:
        min_pyversion = parse_pyversion(cfg["pyversions"]["minimum"])
    except KeyError:
        min_pyversion = parse_pyversion(supported_series[0])
    except ValueError:
        raise click.UsageError(
            f"Invalid setting for pyversions.minimum config option:"
            f' {cfg["pyversions"]["minimum"]!r}: must be in form'
            f" {PYVER_TEMPLATE}"
        )
    try:
        max_pyversion = parse_pyversion(cfg["pyversions"]["maximum"])
    except KeyError:
        max_pyversion = parse_pyversion(supported_series[-1])
    except ValueError:
        raise click.UsageError(
            f"Invalid setting for pyversions.maximum config option:"
            f' {cfg["pyversions"]["maximum"]!r}: must be in form'
            f" {PYVER_TEMPLATE}"
        )
    if min_pyversion > max_pyversion:
        raise click.UsageError(
            "Config option pyversions.minimum cannot be greater than"
            " pyversions.maximum"
        )

    ctx.obj = Config(
        defaults={},
        pyversions=pyver_range(min_pyversion, max_pyversion),
        gh=GitHub(
            token=cfg.get("auth.github", "token", fallback=None),
            headers={"User-Agent": USER_AGENT},
            extra_accept=EXTRA_ACCEPT,
        ),
    )

    if not cfg.has_option("options", "python_requires"):
        cfg["options"]["python_requires"] = f"~={min_pyversion}"

    from .__main__ import main

    for cmdname, cmdobj in main.commands.items():
        defaults: Dict[str, Any] = dict(cfg["options"])
        if cfg.has_section("options." + cmdname):
            defaults.update(cfg["options." + cmdname])
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


def parse_pyversion(s: str) -> PyVersion:
    v = PyVersion.parse(s)
    if v.major not in MAJOR_PYTHON_VERSIONS:
        raise NotImplementedError(
            "Only the following major Python versions are supported:"
            f" {', '.join(map(str, MAJOR_PYTHON_VERSIONS))}"
        )
    return v


def pyver_range(minv: PyVersion, maxv: PyVersion) -> List[PyVersion]:
    if minv.major != maxv.major:
        raise NotImplementedError(
            "Python versions with different major versions not supported"
        )
    return [
        PyVersion.construct(minv.major, i) for i in range(minv.minor, maxv.minor + 1)
    ]
