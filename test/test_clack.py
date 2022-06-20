from __future__ import annotations
from typing import Any
import click
import pytest
from pyrepo.clack import ConfigurableCommand, ConfigurableGroup


@click.group(cls=ConfigurableGroup, allow_config=["foo"])
@click.option("--foo")
@click.option("--bar")
def main(**_: Any) -> None:
    pass


@main.command(cls=ConfigurableCommand, disallow_config=["cleesh"])
@click.option("--gnusto")
@click.option("--cleesh")
@click.option("--foo-bar")
def subcmd(**_: Any) -> None:
    pass


@main.command()
@click.option("--quux")
@click.option("--fiplibs")
def runcmd(**_: Any) -> None:
    pass


@pytest.mark.parametrize(
    "cfgin,cfgout",
    [
        (
            {"foo": "red", "subcmd": {"gnusto": 42, "foo-bar": True}},
            {"foo": "red", "subcmd": {"gnusto": "42", "foo_bar": "True"}},
        ),
        (
            {"bar": "green", "subcmd": {"cleesh": "baz"}, "runcmd": {"quux": 17}},
            {"subcmd": {}},
        ),
        (
            {"subcmd": {"foo_bar": "yes"}},
            {"subcmd": {"foo_bar": "yes"}},
        ),
        ({"subcmd": "notadict"}, {}),
    ],
)
def test_process_config(cfgin: dict[str, Any], cfgout: dict[str, Any]) -> None:
    assert isinstance(main, ConfigurableGroup)
    assert main.process_config(cfgin) == cfgout
