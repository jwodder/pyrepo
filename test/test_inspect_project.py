import json
from operator import attrgetter
from pathlib import Path
from shutil import copyfile
import time
from typing import List
import pytest
from pytest_mock import MockerFixture
from pyrepo import util
from pyrepo.inspecting import (
    InvalidProjectError,
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
    mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert get_commit_years(Path()) == result
    util.readcmd.assert_called_once_with(
        "git", "log", "--format=%ad", "--date=format:%Y", cwd=Path()
    )
    time.localtime.assert_called_once_with()


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
    mocker.patch("time.localtime", return_value=time.localtime(1555438634))
    mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert get_commit_years(Path(), include_now=False) == result
    util.readcmd.assert_called_once_with(
        "git", "log", "--format=%ad", "--date=format:%Y", cwd=Path()
    )
    time.localtime.assert_not_called()


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "valid").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module(dirpath: Path) -> None:
    assert find_module(dirpath) == {
        "import_name": "foobar",
        "is_flat_module": dirpath.name.endswith("flat"),
        "src_layout": False,
    }


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "find_module" / "valid-src").iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_src(dirpath: Path) -> None:
    assert find_module(dirpath) == {
        "import_name": "foobar",
        "is_flat_module": dirpath.name.endswith("flat"),
        "src_layout": True,
    }


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
    with (dirpath / "variables.json").open() as fp:
        assert variables == json.load(fp)
    assert (dirpath / "after.py").read_text() == dest.read_text()


@pytest.mark.parametrize(
    "reqfile",
    sorted((DATA_DIR / "parse_requirements").glob("*.txt")),
    ids=attrgetter("name"),
)
def test_parse_requirements(reqfile: Path) -> None:
    variables = parse_requirements(reqfile)
    assert variables == json.loads(reqfile.with_suffix(".json").read_text())


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "inspect_project").iterdir()),
    ids=attrgetter("name"),
)
def test_inspect_project(dirpath: Path, mocker: MockerFixture) -> None:
    get_default_branch = mocker.patch(
        "pyrepo.inspecting.get_default_branch",
        return_value="master",
    )
    if (dirpath / "_errmsg.txt").exists():
        with pytest.raises(Exception) as excinfo:
            inspect_project(dirpath)
        assert str(excinfo.value) == (dirpath / "_errmsg.txt").read_text().strip()
    else:
        env = inspect_project(dirpath)
        get_default_branch.assert_called_once_with(dirpath)
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
    mocker.patch("pyrepo.util.readcmd", return_value=gitoutput)
    assert get_default_branch(Path()) == result
    util.readcmd.assert_called_once_with(
        "git", "--no-pager", "branch", "--format=%(refname:short)", cwd=Path()
    )


def test_get_default_branch_error(mocker: MockerFixture) -> None:
    mocker.patch("pyrepo.util.readcmd", return_value="foo\nquux")
    with pytest.raises(InvalidProjectError) as excinfo:
        get_default_branch(Path())
    assert str(excinfo.value) == "Could not determine default Git branch"
    util.readcmd.assert_called_once_with(
        "git", "--no-pager", "branch", "--format=%(refname:short)", cwd=Path()
    )
