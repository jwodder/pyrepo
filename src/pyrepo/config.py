from configparser import ConfigParser
from pathlib import Path
import platform
from typing import Any, Dict, List, Tuple, Union
import click
from pydantic import BaseModel
from pyversion_info import get_pyversion_info
import requests
from pyrepo import __url__, __version__
from .gh import ACCEPT, GitHub

DEFAULT_CFG = str(Path.home() / ".config" / "pyrepo.cfg")

DEFAULTS = {
    "options": {
        "author": "Anonymous",
        "author_email": "USER@HOST",
    },
}

USER_AGENT = "pyrepo/{} ({}) requests/{} {}/{}".format(
    __version__,
    __url__,
    requests.__version__,
    platform.python_implementation(),
    platform.python_version(),
)

MAJOR_PYTHON_VERSIONS = [3]
PYVER_TEMPLATE = '"3.X"'


class Config(BaseModel):
    defaults: dict
    pyversions: List[str]
    gh: GitHub

    class Config:
        arbitrary_types_allowed = True


def configure(ctx: click.Context, filename: Union[str, Path]) -> None:
    cfg = ConfigParser(interpolation=None)
    cfg.optionxform = lambda s: s.lower().replace("-", "_")  # type: ignore[assignment]
    cfg.read_dict(DEFAULTS)
    cfg.read(filename)
    ### TODO: Check the return value and raise an exception if it's empty
    supported_series = [
        v for v in get_pyversion_info().supported_series() if not v.startswith("2.")
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

    s = requests.Session()
    s.headers["Accept"] = ACCEPT
    s.headers["User-Agent"] = USER_AGENT
    auth_gh: Dict[str, str]
    try:
        auth_gh = dict(cfg["auth.github"])
    except KeyError:
        auth_gh = {}
    if "token" in auth_gh:
        s.headers["Authorization"] = "token " + auth_gh["token"]
    ctx.obj = Config(
        defaults={},
        pyversions=pyver_range(min_pyversion, max_pyversion),
        gh=GitHub(session=s),
    )

    if not cfg.has_option("options", "python_requires"):
        cfg["options"]["python_requires"] = "~={}.{}".format(*min_pyversion)
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


def parse_pyversion(s: str) -> Tuple[int, int]:
    m1, _, m2 = s.partition(".")
    major = int(m1)
    minor = int(m2)
    if major not in MAJOR_PYTHON_VERSIONS:
        raise NotImplementedError(
            "Only the following major Python versions are supported:"
            f" {', '.join(map(str, MAJOR_PYTHON_VERSIONS))}"
        )
    return (major, minor)


def pyver_range(
    min_pyversion: Tuple[int, int], max_pyversion: Tuple[int, int]
) -> List[str]:
    minmajor, minminor = min_pyversion
    maxmajor, maxminor = max_pyversion
    if minmajor != maxmajor:
        raise NotImplementedError
    return [f"{minmajor}.{i}" for i in range(minminor, maxminor + 1)]
