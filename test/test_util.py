from typing import List
from packaging.specifiers import SpecifierSet
import pytest
from pyrepo.commands.release import next_version
from pyrepo.util import sort_specifier, update_years2str


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
