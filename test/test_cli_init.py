from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture
import responses
from pyrepo.__main__ import main
from test_helpers import DATA_DIR, assert_dirtrees_eq, case_dirs, mock_git, show_result

CONFIG = DATA_DIR / "config.toml"


@case_dirs("pyrepo_init")
@pytest.mark.usefixtures(
    "mock_cpython_supported", "mock_major_pypy_supported", "mock_pypy_supported"
)
def test_pyrepo_init(dirpath: Path, mocker: MockerFixture, tmp_path: Path) -> None:
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(dirpath / "before", tmp_path)
    options = (dirpath / "options.txt").read_text().splitlines()
    if (dirpath / "config.toml").exists():
        cfg = dirpath / "config.toml"
    else:
        cfg = CONFIG
    mgitcls, mgit = mock_git(
        mocker, get_commit_years=[2016, 2018, 2019], get_default_branch="master"
    )
    runcmd = mocker.patch("pyrepo.commands.init.runcmd")
    with responses.RequestsMock() as rsps:
        # Don't step on pyversion-info:
        rsps.add_passthru("https://raw.githubusercontent.com")
        if (dirpath / "github_user.txt").exists():
            rsps.add(
                responses.GET,
                "https://api.github.com/user",
                json={"login": (dirpath / "github_user.txt").read_text().strip()},
            )
            mocker.patch("ghtoken.get_ghtoken", return_value="some_token")
        r = CliRunner().invoke(
            main,
            ["-c", str(cfg), "init"] + options + [str(tmp_path)],
            # Standalone mode needs to be disabled so that `ClickException`s
            # (e.g., `UsageError`) will be returned in `r.exception` instead of
            # a `SystemExit`
            standalone_mode=False,
        )
    if not (dirpath / "errmsg.txt").exists():
        assert r.exit_code == 0, show_result(r)
        mgitcls.assert_called_once_with(dirpath=tmp_path)
        mgit.get_commit_years.assert_called_once_with()
        mgit.get_default_branch.assert_called_once_with()
        runcmd.assert_called_once_with("pre-commit", "install", cwd=tmp_path)
        assert_dirtrees_eq(tmp_path, dirpath / "after")
    else:
        assert r.exit_code != 0 and r.exception is not None, show_result(r)
        assert str(r.exception) == (dirpath / "errmsg.txt").read_text().strip()
