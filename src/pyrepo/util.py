from __future__ import annotations
from collections.abc import Callable, Iterable, Iterator
from datetime import date
from enum import Enum
from functools import partial, wraps
import logging
from operator import attrgetter
from pathlib import Path
import re
import shlex
import subprocess
import sys
from textwrap import fill
import time
from typing import Any, TextIO
from in_place import InPlace
from intspan import intspan
from jinja2 import Environment, PackageLoader
from linesep import ascii_splitlines
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pyversion_info import VersionDatabase

log = logging.getLogger(__name__)


class PyVersion(str):
    __slots__ = ("major", "minor")

    def __init__(self, s: str) -> None:
        if m := re.fullmatch(r"(\d+)\.(\d+)", s):
            self.major = int(m[1])
            self.minor = int(m[2])
        else:
            raise ValueError(f"Invalid Python series: {s!r}")

    def __repr__(self) -> str:
        return f"PyVersion({super().__repr__()})"

    # Using functools.total_ordering to derive everything from __lt__ doesn't
    # work, as the comparison operators inherited from str keep the decorator
    # from working.

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, PyVersion):
            return (self.major, self.minor) < (other.major, other.minor)
        else:
            return NotImplemented

    def __le__(self, other: Any) -> bool:
        if isinstance(other, PyVersion):
            return (self.major, self.minor) <= (other.major, other.minor)
        else:
            return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, PyVersion):
            return (self.major, self.minor) > (other.major, other.minor)
        else:
            return NotImplemented

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, PyVersion):
            return (self.major, self.minor) >= (other.major, other.minor)
        else:
            return NotImplemented

    @classmethod
    def parse(cls, s: Any) -> PyVersion:
        return cls(s)

    @classmethod
    def construct(cls, major: int, minor: int) -> PyVersion:
        return cls.parse(f"{major}.{minor}")

    @property
    def pyenv(self) -> str:
        return f"py{self.major}{self.minor}"


def runcmd(*args: str | Path, **kwargs: Any) -> subprocess.CompletedProcess:
    log.debug("Running: %s", shlex.join(map(str, args)))
    kwargs.setdefault("check", True)
    return subprocess.run(args, **kwargs)


def readcmd(*args: str | Path, **kwargs: Any) -> str:
    kwargs["stdout"] = subprocess.PIPE
    kwargs["text"] = True
    r = runcmd(*args, **kwargs)
    assert isinstance(r.stdout, str)
    return r.stdout.strip()


def ensure_license_years(filepath: str | Path, years: list[int]) -> None:
    map_lines(
        filepath,
        partial(
            replace_group,
            r"^Copyright \(c\) (\d[-,\d\s]+\d) \w+",
            lambda ys: update_years2str(ys, years),
        ),
    )


def years2str(years: list[int]) -> str:
    return str(intspan(years)).replace(",", ", ")


def update_years2str(year_str: str, years: list[int] | None = None) -> str:
    """
    Given a string of years of the form ``"2014, 2016-2017"``, update the
    string if necessary to include the given years (default: the current year).
    """
    if years is None:
        years = [time.localtime().tm_year]
    yearspan = intspan(year_str)
    yearspan.update(years)
    return years2str(yearspan)


def cpython_supported() -> list[str]:
    pyvinfo = VersionDatabase.fetch().cpython
    return [v for v in pyvinfo.minor_versions() if pyvinfo.is_supported(v)]


def pypy_supported(cpython_versions: list[PyVersion]) -> list[PyVersion]:
    # Returns the subset of `cpython_versions` that are supported by the latest
    # PyPy minor version
    info = VersionDatabase.fetch().pypy
    *_, latest_series = filter(info.is_released, info.minor_versions())
    pypy_supports = set(
        map(PyVersion.parse, info.supported_cpython_series(latest_series))
    )
    return sorted(pypy_supports.intersection(cpython_versions))


def major_pypy_supported(cpython_versions: list[PyVersion]) -> list[int]:
    # Returns the subset of major versions of `cpython_versions` that are
    # supported by the latest PyPy minor version
    info = VersionDatabase.fetch().pypy
    *_, latest_series = filter(info.is_released, info.minor_versions())
    pypy_supports = {
        PyVersion.parse(v).major for v in info.supported_cpython_series(latest_series)
    }
    return sorted(pypy_supports.intersection(v.major for v in cpython_versions))


def get_jinja_env() -> Environment:
    jenv = Environment(
        loader=PackageLoader("pyrepo", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    jenv.filters["major_pypy_supported"] = major_pypy_supported
    jenv.filters["pypy_supported"] = pypy_supported
    jenv.filters["rewrap"] = rewrap
    jenv.filters["years2str"] = years2str
    return jenv


def rewrap(s: str) -> str:
    return fill(
        s.replace("\n", " "),
        break_long_words=False,
        break_on_hyphens=False,
        expand_tabs=False,
        fix_sentence_endings=True,
        replace_whitespace=False,
        width=79,
    )


def yield_lines(fp: TextIO) -> Iterator[str]:
    # Like pkg_resources.yield_lines(fp), but without the dependency on
    # pkg_resources
    for line in fp:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def sort_specifier(specset: SpecifierSet) -> str:
    """Stringify a `SpecifierSet`, sorting by each specifier's version"""
    return ", ".join(map(str, sorted(specset, key=attrgetter("version"))))


def replace_group(
    rgx: str | re.Pattern[str],
    replacer: str | Callable[[str], str],
    s: str,
    group: int | str = 1,
) -> str:
    if m := re.search(rgx, s):
        if isinstance(replacer, str):
            repl = replacer
        else:
            repl = replacer(m[group])
        s = s[: m.start(group)] + repl + s[m.end(group) :]
    return s


def map_lines(filepath: str | Path, func: Callable[[str], str]) -> None:
    with InPlace(filepath, mode="t", encoding="utf-8") as fp:
        for line in fp:
            print(func(line), file=fp, end="")


def maybe_map_lines(filepath: str | Path, func: Callable[[str], str | None]) -> None:
    with InPlace(filepath, mode="t", encoding="utf-8") as fp:
        for line in fp:
            if (newline := func(line)) is not None:
                print(newline, file=fp, end="")


def cpe_no_tb(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

    return wrapped


class Bump(Enum):
    MAJOR = 0
    MINOR = 1
    MICRO = 2
    POST = -1
    DATE = -2


def bump_version(v: str | Version, level: Bump) -> str:
    if isinstance(v, Version):
        vobj = v
    else:
        vobj = Version(v)
    if vobj.is_prerelease:
        raise ValueError(f"Cannot bump pre-release versions: {v!r}")
    if level is Bump.POST:
        post = vobj.post if vobj.post is not None else 0
        return mkversion(epoch=vobj.epoch, release=vobj.release, post=post + 1)
    elif level is Bump.DATE:
        today = date.today()
        release: tuple[int, ...] = (today.year, today.month, today.day)
        if vobj.release[:3] == release:
            if len(vobj.release) > 3:
                subver = vobj.release[3] + 1
            else:
                subver = 1
            release += (subver,)
        return mkversion(epoch=vobj.epoch, release=release)
    else:
        vs = list(vobj.release) + [0] * (level.value + 1 - len(vobj.release))
        vs[level.value] += 1
        vs[level.value + 1 :] = [0] * len(vs[level.value + 1 :])
        return mkversion(epoch=vobj.epoch, release=vs)


def mkversion(release: Iterable[int], epoch: int = 0, post: int | None = None) -> str:
    s = ".".join(map(str, release))
    if epoch:
        s = f"{epoch}!{s}"
    if post is not None:
        s += f".post{post}"
    return s


def next_version(v: str, post: bool = False) -> str:
    """
    If ``v`` is a prerelease version, returns the base version.  Otherwise,
    returns the next minor version (or the next postrelease version, if
    ``post`` is true) after the base version.
    """
    vobj = Version(v)
    if vobj.is_prerelease:
        return vobj.base_version
    else:
        return bump_version(vobj, Bump.POST if post else Bump.MINOR)


# Items are returned without trailing newlines
def split_markup_list(s: str) -> list[str]:
    items: list[str] = []
    for ln in ascii_splitlines(s, keepends=True):
        if ln.startswith("- "):
            items.append("")
        elif not items:
            if ln.strip() == "":
                continue
            else:
                raise ValueError("Content before list items")
        items[-1] += ln
    return [it.rstrip("\r\n") for it in items]


def join_markup_list(items: list[str]) -> str:
    items = [it.rstrip("\r\n") for it in items]
    if any("" in ascii_splitlines(it) for it in items):
        joint = "\n\n"
    else:
        joint = "\n"
    return joint.join(items)
