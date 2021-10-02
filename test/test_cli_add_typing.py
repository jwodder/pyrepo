from operator import attrgetter
import os
from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import pytest
from pyrepo.__main__ import main
from test_helpers import DATA_DIR, assert_dirtrees_eq, show_result


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "add_typing").iterdir()),
    ids=attrgetter("name"),
)
@pytest.mark.usefixtures("mock_default_branch")
def test_pyrepo_add_typing(dirpath: Path, tmp_path: Path) -> None:
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(dirpath / "before", tmp_path)
    r = CliRunner().invoke(
        main,
        ["-c", os.devnull, "-C", str(tmp_path), "add-typing"],
        # Standalone mode needs to be disabled so that `ClickException`s (e.g.,
        # `UsageError`) will be returned in `r.exception` instead of a
        # `SystemExit`
        standalone_mode=False,
    )
    assert r.exit_code == 0, show_result(r)
    assert_dirtrees_eq(tmp_path, dirpath / "after")
