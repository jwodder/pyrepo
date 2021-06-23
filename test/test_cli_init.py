import logging
from operator import attrgetter
from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import pytest
import responses
from pyrepo.__main__ import main
from test_helpers import DATA_DIR, assert_dirtrees_eq, show_result

CONFIG = DATA_DIR / "config.cfg"


@pytest.mark.parametrize(
    "dirpath",
    sorted((DATA_DIR / "pyrepo_init").iterdir()),
    ids=attrgetter("name"),
)
def test_pyrepo_init(caplog, dirpath, mocker, tmp_path):
    caplog.set_level(logging.INFO)  # to catch errors in logging statements
    tmp_path /= "tmp"  # copytree() can't copy to a dir that already exists
    copytree(dirpath / "before", tmp_path)
    options = (dirpath / "options.txt").read_text().splitlines()
    if (dirpath / "config.cfg").exists():
        cfg = dirpath / "config.cfg"
    else:
        cfg = CONFIG
    get_commit_years = mocker.patch(
        "pyrepo.inspecting.get_commit_years",
        return_value=[2016, 2018, 2019],
    )
    get_default_branch = mocker.patch(
        "pyrepo.inspecting.get_default_branch",
        return_value="master",
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
        r = CliRunner().invoke(
            main,
            ["-c", str(cfg), "-C", str(tmp_path), "init"] + options,
            # Standalone mode needs to be disabled so that `ClickException`s
            # (e.g., `UsageError`) will be returned in `r.exception` instead of
            # a `SystemExit`
            standalone_mode=False,
        )
    if not (dirpath / "errmsg.txt").exists():
        assert r.exit_code == 0, show_result(r)
        get_commit_years.assert_called_once_with(Path())
        get_default_branch.assert_called_once_with(Path())
        runcmd.assert_called_once_with("pre-commit", "install")
        assert_dirtrees_eq(tmp_path, dirpath / "after")
    else:
        assert r.exit_code != 0 and r.exception is not None, show_result(r)
        assert str(r.exception) == (dirpath / "errmsg.txt").read_text().strip()
