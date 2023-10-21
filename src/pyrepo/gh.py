from __future__ import annotations
from ghreq import Client, make_user_agent
import ghtoken  # Module import for mocking purposes
from . import __url__, __version__


class GitHub(Client):
    def __init__(self) -> None:
        super().__init__(
            token=ghtoken.get_ghtoken(),
            user_agent=make_user_agent("jwodder-pyrepo", __version__, url=__url__),
        )
