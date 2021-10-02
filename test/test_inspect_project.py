import json
from operator import attrgetter
from pathlib import Path
from shutil import copyfile
import time
from typing import List
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from pyrepo.inspecting import (
    InvalidProjectError,
    ModuleInfo,
    Requirements,
    extract_requires,
    find_module,
    get_commit_years,
    get_default_branch,
    inspect_project,
    parse_requirements,
)
from pyrepo.project import Project
from test_helpers import DATA_DIR


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
    gitoutput: str, result: List[int], mocker: MockerFixture
) -> None:
    # Set current time to 2019-04-16T18:17:14Z:
    mlocaltime = mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mreadcmd = mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert get_commit_years(Path()) == result
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
    gitoutput: str, result: List[int], mocker: MockerFixture
) -> None:
    # Set current time to 2019-04-16T18:17:14Z:
    mlocaltime = mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mreadcmd = mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert get_commit_years(Path(), include_now=False) == result
    mreadcmd.assert_called_once_with(
        "git", "log", "--format=%ad", "--date=format:%Y", cwd=Path()
    )
    mlocaltime.assert_not_called()


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "valid").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module(dirpath: Path) -> None:
    assert find_module(dirpath) == ModuleInfo(
        import_name="foobar",
        is_flat_module=dirpath.name.endswith("flat"),
        src_layout=False,
    )


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "valid-src").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_src(dirpath: Path) -> None:
    assert find_module(dirpath) == ModuleInfo(
        import_name="foobar",
        is_flat_module=dirpath.name.endswith("flat"),
        src_layout=True,
    )


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "extra").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_extra(dirpath: Path) -> None:
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == "Multiple Python modules in repository"


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "none").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_none(dirpath: Path) -> None:
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == "No Python modules in repository"


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "extract_requires").iterdir()),
    ids=attrgetter("name"),
)
def test_extract_requires(dirpath: Path, tmp_path: Path) -> None:
    dest = tmp_path / "foobar.py"
    copyfile(dirpath / "before.py", dest)
    variables = extract_requires(dest)
    assert variables == Requirements.parse_file(dirpath / "variables.json")
    assert (dirpath / "after.py").read_text() == dest.read_text()


@pytest.mark.parametrize(
    "reqfile",
    sorted((DATA_DIR / "parse_requirements").glob("*.txt")),
    ids=attrgetter("name"),
)
def test_parse_requirements(reqfile: Path) -> None:
    variables = parse_requirements(reqfile)
    assert variables == Requirements.parse_file(reqfile.with_suffix(".json"))


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "inspect_project").iterdir()),
    ids=attrgetter("name"),
)
def test_inspect_project(mock_default_branch: MagicMock, dirpath: Path) -> None:
    if (dirpath / "_errmsg.txt").exists():
        with pytest.raises(Exception) as excinfo:
            inspect_project(dirpath)
        assert str(excinfo.value) == (dirpath / "_errmsg.txt").read_text().strip()
    else:
        env = inspect_project(dirpath)
        mock_default_branch.assert_called_once_with(dirpath)
        assert env == json.loads((dirpath / "_inspect.json").read_text())
        project = Project.from_inspection(dirpath, env)
        assert project.get_template_context() == env


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
    assert get_default_branch(Path()) == result
    m.assert_called_once_with(
        "git", "--no-pager", "branch", "--format=%(refname:short)", cwd=Path()
    )


def test_get_default_branch_error(mocker: MockerFixture) -> None:
    m = mocker.patch("pyrepo.util.readcmd", return_value="foo\nquux")
    with pytest.raises(InvalidProjectError) as excinfo:
        get_default_branch(Path())
    assert str(excinfo.value) == "Could not determine default Git branch"
    m.assert_called_once_with(
        "git", "--no-pager", "branch", "--format=%(refname:short)", cwd=Path()
    )
