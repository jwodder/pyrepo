import logging
from typing import List
import pytest
from pyrepo import util


@pytest.fixture(autouse=True)
def capture_all_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="pyrepo")


@pytest.fixture
def mock_pypy_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    def mocked(cpython_versions: List[util.PyVersion]) -> List[util.PyVersion]:
        pypy_supports = {"2.7", "3.6", "3.7", "3.8"}
        return [cpy for cpy in cpython_versions if cpy in pypy_supports]

    monkeypatch.setattr(util, "pypy_supported", mocked)
