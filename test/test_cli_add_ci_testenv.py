import os
from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture
from pyrepo.__main__ import main
from test_helpers import assert_dirtrees_eq, case_dirs, mock_git, show_result


@case_dirs("add_ci_testenv")
@pytest.mark.usefixtures("mock_pypy_supported")
def test_pyrepo_add_ci_testenv(
    dirpath: Path, mocker: MockerFixture, tmp_path: Path
) -> None:
    mgitcls, mgit = mock_git(mocker, get_default_branch="master")
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(dirpath / "before", tmp_path)
    args = (dirpath / "args.txt").read_text().splitlines()
    r = CliRunner().invoke(
        main,
        ["-c", os.devnull, "-C", str(tmp_path), "add-ci-testenv"] + args,
        # Standalone mode needs to be disabled so that `ClickException`s (e.g.,
        # `UsageError`) will be returned in `r.exception` instead of a
        # `SystemExit`
        standalone_mode=False,
    )
    assert r.exit_code == 0, show_result(r)
    mgitcls.assert_called_once_with(dirpath=Path())
    mgit.get_default_branch.assert_called_once_with()
    assert_dirtrees_eq(tmp_path, dirpath / "after")
