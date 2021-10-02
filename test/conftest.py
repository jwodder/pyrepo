import logging
import pytest
from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def capture_all_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="pyrepo")


@pytest.fixture
def default_branch(mocker: MockerFixture) -> None:
    mocker.patch("pyrepo.inspecting.get_default_branch", return_value="master")
