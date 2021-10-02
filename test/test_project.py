from shutil import copytree
import pytest
from pyrepo.project import Project
from test_helpers import DATA_DIR, assert_dirtrees_eq


@pytest.mark.usefixtures("default_branch")
def test_add_pyversion(tmp_path):
    CASE_DIR = DATA_DIR / "add_pyversion"
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(CASE_DIR / "before", tmp_path)
    proj = Project.from_directory(tmp_path)
    proj.add_pyversion("3.9")
    assert_dirtrees_eq(tmp_path, CASE_DIR / "after")
