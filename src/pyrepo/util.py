import logging
from operator import attrgetter
import re
import shlex
import subprocess
import sys
from textwrap import wrap
import time
from typing import List, Optional, Tuple
import click
from in_place import InPlace
from intspan import intspan
from jinja2 import Environment, PackageLoader
from linesep import split_preceded

log = logging.getLogger(__name__)


def runcmd(*args, **kwargs):
    log.debug("Running: %s", " ".join(map(shlex.quote, args)))
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)


def readcmd(*args, **kwargs):
    log.debug("Running: %s", " ".join(map(shlex.quote, args)))
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
    return "\n".join(
        wrap(
            s.replace("\n", " "),
            break_long_words=False,
            break_on_hyphens=False,
            expand_tabs=False,
            fix_sentence_endings=True,
            replace_whitespace=False,
            width=79,
        )
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


def is_blank(line):
    return line in ("\n", "\r\n")


def read_paragraphs(fp):
    para = []
    for line in fp:
        if not is_blank(line) and para and is_blank(para[-1]):
            yield "".join(para)
            para = [line]
        else:
            para.append(line)
    if para:
        yield "".join(para)


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
