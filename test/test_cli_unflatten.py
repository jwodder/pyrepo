from operator import attrgetter
import os
from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture
from pyrepo.__main__ import main
from test_helpers import DATA_DIR, assert_dirtrees_eq, mock_git, show_result


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "unflatten").iterdir()),
    ids=attrgetter("name"),
)
def test_pyrepo_unflatten(dirpath: Path, mocker: MockerFixture, tmp_path: Path) -> None:
    mgitcls, mgit = mock_git(mocker, get_default_branch="master")
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(dirpath / "before", tmp_path)
    r = CliRunner().invoke(
        main,
        ["-c", os.devnull, "-C", str(tmp_path), "unflatten"],
        # Standalone mode needs to be disabled so that `ClickException`s (e.g.,
        # `UsageError`) will be returned in `r.exception` instead of a
        # `SystemExit`
        standalone_mode=False,
    )
    assert r.exit_code == 0, show_result(r)
    mgitcls.assert_called_once_with(dirpath=Path())
    mgit.get_default_branch.assert_called_once_with()
    assert_dirtrees_eq(tmp_path, dirpath / "after")
