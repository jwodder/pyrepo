from __future__ import annotations
from pathlib import Path
import time
import pytest
from pytest_mock import MockerFixture
from pyrepo.git import Git
from pyrepo.inspecting import InvalidProjectError


@pytest.mark.parametrize(
    "gitoutput,result",
    [
        ("2019\n2019\n2018\n2016", [2016, 2018, 2019]),
        ("2018\n2016", [2016, 2018, 2019]),
        ("2019", [2019]),
        ("", [2019]),
        ("2018", [2018, 2019]),
    ],
)
def test_get_commit_years_include_now(
    gitoutput: str, result: list[int], mocker: MockerFixture
) -> None:
    # Set current time to 2019-04-16T18:17:14Z:
    mlocaltime = mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mreadcmd = mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert Git(dirpath=Path()).get_commit_years() == result
    mreadcmd.assert_called_once_with(
        "git", "log", "--format=%ad", "--date=format:%Y", cwd=Path()
    )
    mlocaltime.assert_called_once_with()


@pytest.mark.parametrize(
    "gitoutput,result",
    [
        ("2019\n2019\n2018\n2016", [2016, 2018, 2019]),
        ("2018\n2016", [2016, 2018]),
        ("2019", [2019]),
        ("", []),
        ("2018", [2018]),
    ],
)
def test_get_commit_years_no_include_now(
    gitoutput: str, result: list[int], mocker: MockerFixture
) -> None:
    # Set current time to 2019-04-16T18:17:14Z:
    mlocaltime = mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mreadcmd = mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert Git(dirpath=Path()).get_commit_years(include_now=False) == result
    mreadcmd.assert_called_once_with(
        "git", "log", "--format=%ad", "--date=format:%Y", cwd=Path()
    )
    mlocaltime.assert_not_called()


@pytest.mark.parametrize(
    "gitoutput,result",
    [
        ("foo\nmaster\nquux", "master"),
        ("foo\nmain\nquux", "main"),
        ("foo\nmain\nmaster\nquux", "main"),
    ],
)
def test_get_default_branch(gitoutput: str, result: str, mocker: MockerFixture) -> None:
    m = mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert Git(dirpath=Path()).get_default_branch() == result
    m.assert_called_once_with("git", "branch", "--format=%(refname:short)", cwd=Path())


def test_get_default_branch_error(mocker: MockerFixture) -> None:
    m = mocker.patch("pyrepo.util.readcmd", return_value="foo\nquux")
    with pytest.raises(InvalidProjectError) as excinfo:
        Git(dirpath=Path()).get_default_branch()
    assert str(excinfo.value) == "Could not determine default Git branch"
    m.assert_called_once_with("git", "branch", "--format=%(refname:short)", cwd=Path())
