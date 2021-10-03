from operator import attrgetter
from pathlib import Path
from traceback import format_exception
from typing import Any, Tuple
from unittest.mock import MagicMock
from click.testing import Result
from pytest_mock import MockerFixture

DATA_DIR = Path(__file__).with_name("data")


def assert_dirtrees_eq(tree1: Path, tree2: Path) -> None:
    assert sorted(map(attrgetter("name"), tree1.iterdir())) == sorted(
        map(attrgetter("name"), tree2.iterdir())
    )
    for p1 in tree1.iterdir():
        p2 = tree2 / p1.name
        assert p1.is_dir() == p2.is_dir()
        if p1.is_dir():
            assert_dirtrees_eq(p1, p2)
        else:
            assert p1.read_text() == p2.read_text()


def show_result(r: Result) -> str:
    if r.exception is not None:
        assert isinstance(r.exc_info, tuple)
        return "".join(format_exception(*r.exc_info))
    else:
        return r.output


def mock_git(mocker: MockerFixture, **kwargs: Any) -> Tuple[MagicMock, MagicMock]:
    instance = MagicMock(**{f"{k}.return_value": v for k, v in kwargs.items()})
    cls = mocker.patch("pyrepo.git.Git", return_value=instance)
    return (cls, instance)
