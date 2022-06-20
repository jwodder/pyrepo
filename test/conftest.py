from __future__ import annotations
import logging
import pytest
from pytest_mock import MockerFixture
from pyrepo import util


@pytest.fixture(autouse=True)
def capture_all_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="pyrepo")


@pytest.fixture
def mock_pypy_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    def mocked(cpython_versions: list[util.PyVersion]) -> list[util.PyVersion]:
        pypy_supports = {"2.7", "3.6", "3.7", "3.8"}
        return [cpy for cpy in cpython_versions if cpy in pypy_supports]

    monkeypatch.setattr(util, "pypy_supported", mocked)


@pytest.fixture
def mock_major_pypy_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    def mocked(cpython_versions: list[util.PyVersion]) -> list[int]:
        pypy_supports = {3}
        return sorted(pypy_supports.intersection(cpy.major for cpy in cpython_versions))

    monkeypatch.setattr(util, "major_pypy_supported", mocked)


@pytest.fixture
def mock_cpython_supported(mocker: MockerFixture) -> None:
    mocker.patch(
        "pyrepo.util.cpython_supported", return_value=["3.5", "3.6", "3.7", "3.8"]
    )
