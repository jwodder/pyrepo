import json
from operator import attrgetter
from pathlib import Path
from shutil import copyfile
import pytest
from pytest_mock import MockerFixture
from pyrepo.inspecting import (
    InvalidProjectError,
    ModuleInfo,
    Requirements,
    extract_requires,
    find_module,
    inspect_project,
    parse_requirements,
)
from pyrepo.project import Project
from test_helpers import DATA_DIR, mock_git


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
def test_inspect_project(mocker: MockerFixture, dirpath: Path) -> None:
    mgitcls, mgit = mock_git(mocker, get_default_branch="master")
    if (dirpath / "_errmsg.txt").exists():
        with pytest.raises(Exception) as excinfo:
            inspect_project(dirpath)
        assert str(excinfo.value) == (dirpath / "_errmsg.txt").read_text().strip()
    else:
        env = inspect_project(dirpath)
        mgitcls.assert_called_once_with(dirpath=dirpath)
        mgit.get_default_branch.assert_called_once_with()
        assert env == json.loads((dirpath / "_inspect.json").read_text())
        project = Project.from_inspection(dirpath, env)
        assert project.get_template_context() == env
