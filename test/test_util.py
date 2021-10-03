import json
from typing import List
from packaging.specifiers import SpecifierSet
import pytest
from pyrepo.commands.release import next_version
from pyrepo.util import PyVersion, sort_specifier, update_years2str


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
def test_update_years2str(year_str: str, years: List[int], result: str) -> None:
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
