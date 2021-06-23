import pytest


@pytest.fixture
def default_branch(mocker):
    mocker.patch("pyrepo.inspecting.get_default_branch", return_value="master")
