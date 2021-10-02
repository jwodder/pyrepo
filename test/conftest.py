import logging
import pytest


@pytest.fixture(autouse=True)
def capture_all_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="pyrepo")


@pytest.fixture
def default_branch(mocker):
    mocker.patch("pyrepo.inspecting.get_default_branch", return_value="master")
