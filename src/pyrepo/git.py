from __future__ import annotations
import logging
from pathlib import Path
import subprocess
import time
from typing import Any, Optional
from pydantic import BaseModel, DirectoryPath
from . import util

log = logging.getLogger(__name__)


class Git(BaseModel):
    dirpath: DirectoryPath

    def run(self, *args: str | Path, **kwargs: Any) -> subprocess.CompletedProcess:
        return util.runcmd("git", *args, cwd=self.dirpath, **kwargs)

    def read(self, *args: str | Path) -> str:
        return util.readcmd("git", *args, cwd=self.dirpath)

    def readlines(self, *args: str | Path) -> list[str]:
        return self.read(*args).splitlines()

    def get_remotes(self) -> list[str]:
        return self.readlines("remote")

    def rm_remote(self, remote: str) -> None:
        self.run("remote", "rm", remote)

    def add_remote(self, remote: str, url: str) -> None:
        self.run("remote", "add", remote, url)

    def get_commit_years(self, include_now: bool = True) -> list[int]:
        years = set(map(int, self.readlines("log", "--format=%ad", "--date=format:%Y")))
        if include_now:
            years.add(time.localtime().tm_year)
        return sorted(years)

    def get_default_branch(self) -> str:
        from .inspecting import InvalidProjectError

        branches = set(self.readlines("branch", "--format=%(refname:short)"))
        for guess in ["main", "master"]:
            if guess in branches:
                return guess
        raise InvalidProjectError("Could not determine default Git branch")

    def get_latest_tag(self) -> Optional[str]:
        tags = self.readlines("tag", "-l", "--sort=-creatordate")
        if tags:
            return tags[0]
        else:
            return None

    def get_config(self, key: str, default: Optional[str]) -> Optional[str]:
        if default is not None:
            opts = ["--default", default]
        else:
            opts = []
        try:
            return self.read("config", "--get", *opts, key)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                return None
            else:
                raise
