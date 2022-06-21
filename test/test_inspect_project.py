import json
from operator import attrgetter
from pathlib import Path
from shutil import copyfile
import pytest
from pytest_mock import MockerFixture
from pyrepo.details import ProjectDetails
from pyrepo.inspecting import (
    InvalidProjectError,
    ModuleInfo,
    Requirements,
    extract_requires,
    find_module,
    parse_requirements,
)
from test_helpers import DATA_DIR, case_dirs, mock_git


@case_dirs("find_module", "valid")
def test_find_module(dirpath: Path) -> None:
    assert find_module(dirpath) == ModuleInfo(
        import_name="foobar",
        is_flat_module=dirpath.name.endswith("flat"),
        src_layout=False,
    )


@case_dirs("find_module", "valid-src")
def test_find_module_src(dirpath: Path) -> None:
    assert find_module(dirpath) == ModuleInfo(
        import_name="foobar",
        is_flat_module=dirpath.name.endswith("flat"),
        src_layout=True,
    )


@case_dirs("find_module", "extra")
def test_find_module_extra(dirpath: Path) -> None:
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == "Multiple Python modules in repository"


@case_dirs("find_module", "none")
def test_find_module_none(dirpath: Path) -> None:
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == "No Python modules in repository"


@case_dirs("extract_requires")
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


@case_dirs("inspect_project")
def test_inspect_project(dirpath: Path, mocker: MockerFixture) -> None:
    mgitcls, mgit = mock_git(mocker, get_default_branch="master")
    if (dirpath / "_errmsg.txt").exists():
        with pytest.raises(Exception) as excinfo:
            ProjectDetails.inspect(dirpath)
        assert str(excinfo.value) == (dirpath / "_errmsg.txt").read_text().strip()
    else:
        details = ProjectDetails.inspect(dirpath)
        mgitcls.assert_called_once_with(dirpath=dirpath)
        mgit.get_default_branch.assert_called_once_with()
        assert details.for_json() == json.loads((dirpath / "_inspect.json").read_text())
