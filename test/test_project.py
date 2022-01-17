from pathlib import Path
from shutil import copytree
from pytest_mock import MockerFixture
from pyrepo.project import Project
from test_helpers import DATA_DIR, assert_dirtrees_eq, mock_git


def test_add_pyversion(mocker: MockerFixture, tmp_path: Path) -> None:
    mgitcls, mgit = mock_git(mocker, get_default_branch="master")
    CASE_DIR = DATA_DIR / "add_pyversion"
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(CASE_DIR / "before", tmp_path)
    proj = Project.from_directory(tmp_path)
    proj.add_pyversion("3.9")
    mgitcls.assert_called_once_with(dirpath=tmp_path)
    mgit.get_default_branch.assert_called_once_with()
    assert_dirtrees_eq(tmp_path, CASE_DIR / "after")
