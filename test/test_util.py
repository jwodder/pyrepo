from __future__ import annotations
from collections.abc import Iterator
import json
from pathlib import Path
import shutil
import time
from typing import Optional
from packaging.specifiers import SpecifierSet
import pytest
from pytest_mock import MockerFixture
from pyrepo.commands.release import advance_devstatus, get_mime_type
from pyrepo.util import (
    Bump,
    PyVersion,
    bump_version,
    mkversion,
    next_version,
    sort_specifier,
    update_years2str,
)
from test_helpers import case_dirs


@pytest.mark.parametrize(
    "year_str,years,result",
    [
        ("2015", [2015], "2015"),
        ("2015", [2016], "2015-2016"),
        ("2015", [2017], "2015, 2017"),
        ("2014-2015", [2016], "2014-2016"),
        ("2013, 2015", [2016], "2013, 2015-2016"),
        ("2013, 2015", [2017, 2014], "2013-2015, 2017"),
    ],
)
def test_update_years2str(year_str: str, years: list[int], result: str) -> None:
    assert update_years2str(year_str, years) == result


def test_sort_specifier() -> None:
    assert (
        sort_specifier(
            SpecifierSet(">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4")
        )
        == ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4"
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("0.5.0", "0.6.0"),
        ("0.5.1", "0.6.0"),
        ("0.5.0.post1", "0.6.0"),
        ("0.5.1.post1", "0.6.0"),
        ("0.5.0a1", "0.5.0"),
        ("0.5.1a1", "0.5.1"),
        ("0.5.0.dev1", "0.5.0"),
        ("0.5.1.dev1", "0.5.1"),
        ("1!0.5.0", "1!0.6.0"),
    ],
)
def test_next_version(old: str, new: str) -> None:
    assert next_version(old) == new


@pytest.mark.parametrize(
    "vstr,major,minor,pyenv",
    [
        ("3.0", 3, 0, "py30"),
        ("3.6", 3, 6, "py36"),
        ("3.10", 3, 10, "py310"),
    ],
)
def test_pyversion(vstr: str, major: int, minor: int, pyenv: str) -> None:
    v = PyVersion.parse(vstr)
    assert v == vstr
    assert str(v) == vstr
    assert repr(v) == f"PyVersion({vstr!r})"
    assert v.major == major
    assert v.minor == minor
    assert v.pyenv == pyenv
    assert PyVersion.construct(major, minor) == v
    assert json.dumps(v) == f'"{vstr}"'


def test_pyversion_cmp() -> None:
    VERSIONS = list(map(PyVersion.parse, ["2.0", "2.7", "3.0", "3.6", "3.10"]))
    for i in range(len(VERSIONS) - 1):
        assert VERSIONS[i] == VERSIONS[i]
        assert VERSIONS[i] >= VERSIONS[i]
        assert VERSIONS[i] <= VERSIONS[i]
        assert VERSIONS[i] != VERSIONS[i + 1]
        assert VERSIONS[i] < VERSIONS[i + 1]
        assert VERSIONS[i + 1] > VERSIONS[i]
        assert VERSIONS[i] <= VERSIONS[i + 1]
        assert VERSIONS[i + 1] >= VERSIONS[i]


@pytest.mark.parametrize(
    "epoch,release,post,v",
    [
        (0, (1, 2, 3), None, "1.2.3"),
        (1, (1, 2, 3), None, "1!1.2.3"),
        (0, (1, 2, 3), 0, "1.2.3.post0"),
        (0, (1, 2, 3), 1, "1.2.3.post1"),
        (2, (1, 2, 3), 3, "2!1.2.3.post3"),
    ],
)
def test_mkversion(
    epoch: int, release: tuple[int, ...], post: Optional[int], v: str
) -> None:
    assert mkversion(epoch=epoch, release=release, post=post) == v


@pytest.fixture()
def use_fixed_time(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setenv("TZ", "EST5EDT,M3.2.0,M11.1.0")
        time.tzset()
        mocker.patch("time.time", return_value=1612373696)
        # Time is now 2021-02-03T12:34:56-05:00
        yield
    time.tzset()


@pytest.mark.usefixtures("use_fixed_time")
@pytest.mark.parametrize(
    "v1,bump,v2",
    [
        ("0.5.0", Bump.MAJOR, "1.0.0"),
        ("0.5.0.post1", Bump.MAJOR, "1.0.0"),
        ("1!0.5.0", Bump.MAJOR, "1!1.0.0"),
        ("1!2.0.3.post1", Bump.MAJOR, "1!3.0.0"),
        ("1", Bump.MAJOR, "2"),
        ("1.2.3", Bump.MAJOR, "2.0.0"),
        ("1.2.3.4", Bump.MAJOR, "2.0.0.0"),
        ("0.5.0", Bump.MINOR, "0.6.0"),
        ("0.5.0.post1", Bump.MINOR, "0.6.0"),
        ("1!0.5.0", Bump.MINOR, "1!0.6.0"),
        ("1!2.0.3.post1", Bump.MINOR, "1!2.1.0"),
        ("1", Bump.MINOR, "1.1"),
        ("1.2.3", Bump.MINOR, "1.3.0"),
        ("1.2.3.4", Bump.MINOR, "1.3.0.0"),
        ("0.5.0", Bump.MICRO, "0.5.1"),
        ("0.5.0.post1", Bump.MICRO, "0.5.1"),
        ("1!0.5.0", Bump.MICRO, "1!0.5.1"),
        ("1!2.0.3.post1", Bump.MICRO, "1!2.0.4"),
        ("1", Bump.MICRO, "1.0.1"),
        ("1.2.3", Bump.MICRO, "1.2.4"),
        ("1.2.3.4", Bump.MICRO, "1.2.4.0"),
        ("0.5.0", Bump.POST, "0.5.0.post1"),
        ("0.5.0.post1", Bump.POST, "0.5.0.post2"),
        ("1!0.5.0", Bump.POST, "1!0.5.0.post1"),
        ("1!2.0.3.post1", Bump.POST, "1!2.0.3.post2"),
        ("1", Bump.POST, "1.post1"),
        ("1.2.3", Bump.POST, "1.2.3.post1"),
        ("1.2.3.4", Bump.POST, "1.2.3.4.post1"),
        ("1.2.3", Bump.DATE, "2021.2.3"),
        ("1!1.2.3", Bump.DATE, "1!2021.2.3"),
        ("2021.2.3", Bump.DATE, "2021.2.3.1"),
        ("2021.2.3.4.5", Bump.DATE, "2021.2.3.5"),
        ("1!2021.2.3", Bump.DATE, "1!2021.2.3.1"),
    ],
)
def test_bump_version(v1: str, bump: Bump, v2: str) -> None:
    assert bump_version(v1, bump) == v2


@pytest.mark.parametrize("v", ["0.5.0.dev1", "0.5.0a1"])
@pytest.mark.parametrize("bump", list(Bump))
def test_bump_version_prerelease(v: str, bump: Bump) -> None:
    with pytest.raises(ValueError) as excinfo:
        bump_version(v, bump)
    assert str(excinfo.value) == f"Cannot bump pre-release versions: {v!r}"


@case_dirs("advance_devstatus")
def test_advance_devstatus(dirpath: Path, tmp_path: Path) -> None:
    shutil.copyfile(dirpath / "before.cfg", tmp_path / "setup.cfg")
    advance_devstatus(tmp_path / "setup.cfg")
    assert (tmp_path / "setup.cfg").read_text(encoding="utf-8") == (
        dirpath / "after.cfg"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "filename,mtype",
    [
        ("foo.txt", "text/plain"),
        ("foo", "application/octet-stream"),
        ("foo.gz", "application/gzip"),
        ("foo.tar.gz", "application/gzip"),
        ("foo.tgz", "application/gzip"),
        ("foo.taz", "application/gzip"),
        ("foo.svg.gz", "application/gzip"),
        ("foo.svgz", "application/gzip"),
        ("foo.Z", "application/x-compress"),
        ("foo.tar.Z", "application/x-compress"),
        ("foo.bz2", "application/x-bzip2"),
        ("foo.tar.bz2", "application/x-bzip2"),
        ("foo.tbz2", "application/x-bzip2"),
        ("foo.xz", "application/x-xz"),
        ("foo.tar.xz", "application/x-xz"),
        ("foo.txz", "application/x-xz"),
    ],
)
def test_get_mime_type(filename: str, mtype: str) -> None:
    assert get_mime_type(filename) == mtype
