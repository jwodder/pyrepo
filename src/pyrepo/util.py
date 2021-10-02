from functools import total_ordering
import logging
from operator import attrgetter
import re
import shlex
import subprocess
import sys
from textwrap import fill
import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple
import click
from in_place import InPlace
from intspan import intspan
from jinja2 import Environment, PackageLoader
from linesep import split_preceded
from pydantic import parse_obj_as
from pydantic.validators import str_validator

if TYPE_CHECKING:
    from pydantic.typing import CallableGenerator

log = logging.getLogger(__name__)


@total_ordering
class PyVersion(str):
    major: int
    minor: int

    def __init__(self, s: str) -> None:
        major, _, minor = s.partition(".")
        self.major = int(major)
        self.minor = int(minor)

    @classmethod
    def __get_validators__(cls) -> "CallableGenerator":
        yield str_validator
        yield cls._validate
        yield cls

    @classmethod
    def _validate(cls, s: str) -> str:
        if re.fullmatch(r"(\d+)\.(\d+)", s):
            return s
        else:
            raise ValueError(f"Invalid Python series: {s!r}")

    def __repr__(self) -> str:
        return f"PyVersion({super().__repr__()})"

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, PyVersion):
            return (self.major, self.minor) < (other.major, other.minor)
        else:
            return NotImplemented

    @classmethod
    def parse(cls, s: Any) -> "PyVersion":
        return parse_obj_as(cls, s)

    @property
    def pyenv(self) -> str:
        ### TODO: How will tox handle 3.10?
        return f"py{self.major}{self.minor}"


def runcmd(*args, **kwargs):
    log.debug("Running: %s", " ".join(shlex.quote(str(a)) for a in args))
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)


def readcmd(*args, **kwargs):
    log.debug("Running: %s", " ".join(shlex.quote(str(a)) for a in args))
    try:
        return subprocess.check_output(args, universal_newlines=True, **kwargs).strip()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


def ensure_license_years(filepath, years: List[int]) -> None:
    with InPlace(filepath, mode="t", encoding="utf-8") as fp:
        for line in fp:
            m = re.match(r"^Copyright \(c\) (\d[-,\d\s]+\d) \w+", line)
            if m:
                line = (
                    line[: m.start(1)]
                    + update_years2str(m.group(1), years)
                    + line[m.end(1) :]
                )
            print(line, file=fp, end="")


def years2str(years):
    return str(intspan(years)).replace(",", ", ")


def update_years2str(year_str: str, years: Optional[List[int]] = None) -> str:
    """
    Given a string of years of the form ``"2014, 2016-2017"``, update the
    string if necessary to include the given years (default: the current year).
    """
    if years is None:
        years = [time.localtime().tm_year]
    yearspan = intspan(year_str)
    yearspan.update(years)
    return years2str(yearspan)


def get_jinja_env():
    jenv = Environment(
        loader=PackageLoader("pyrepo", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    jenv.filters["repr"] = repr
    jenv.filters["rewrap"] = rewrap
    jenv.filters["years2str"] = years2str
    return jenv


def rewrap(s):
    return fill(
        s.replace("\n", " "),
        break_long_words=False,
        break_on_hyphens=False,
        expand_tabs=False,
        fix_sentence_endings=True,
        replace_whitespace=False,
        width=79,
    )


def optional(*decls, nilstr=False, **attrs):
    """
    Like `click.option`, but no value (not even `None`) is passed to the
    command callback if the user doesn't use the option.  If ``nilstr`` is
    true, ``--opt ""`` will be converted to either `None` or (if ``multiple``)
    ``[]``.
    """

    def callback(ctx, param, value):
        if attrs.get("multiple"):
            if nilstr and value == ("",):
                ctx.params[param.name] = []
            elif value != ():
                ctx.params[param.name] = value
        else:
            if nilstr and value == "":
                ctx.params[param.name] = None
            elif value is not None:
                ctx.params[param.name] = value

    if not attrs.get("multiple"):
        attrs["default"] = None
    return click.option(*decls, callback=callback, expose_value=False, **attrs)


def yield_lines(fp):
    # Like pkg_resources.yield_lines(fp), but without the dependency on
    # pkg_resources
    for line in fp:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def sort_specifier(specset):
    """Stringify a `SpecifierSet`, sorting by each specifier's version"""
    return ", ".join(map(str, sorted(specset, key=attrgetter("version"))))


def split_ini_sections(s: str) -> List[Tuple[Optional[str], str]]:
    """
    Splits an INI file into a list of (section name, sections) pairs.  A given
    section name is `None` iff the "section" is leading whitespace and/or
    comments in the file. Each section includes the `[section name]` line and
    any trailing newlines.
    """
    sect_rgx = re.compile(r"^\[([^]]+)\]$", flags=re.M)
    for sect in split_preceded(s, sect_rgx, retain=True):
        m = sect_rgx.match(sect)
        sect_name = m and m[1]
        yield (sect_name, sect)
