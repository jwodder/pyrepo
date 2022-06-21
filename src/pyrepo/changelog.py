from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import IO, List, Optional
from .util import JSONable

DATE_VERSION = re.compile(r"v\d{4}\.\d?\d\.\d?\d")


@dataclass
class Changelog(JSONable):
    """
    See <https://github.com/jwodder/pyrepo/wiki/CHANGELOG-Format> for a
    description of the format parsed & emitted by this class
    """

    intro: str
    sections: List[ChangelogSection]

    @classmethod
    def load(cls, fp: IO[str]) -> Changelog:
        intro = ""
        prev: Optional[str] = None
        sections: list[ChangelogSection] = []
        for line in fp:
            if re.fullmatch(r"---+\s*", line):
                if sections:
                    sections[-1]._end()
                if prev is None:
                    raise ValueError("File begins with hrule")
                if m := re.fullmatch(
                    (
                        r"(?P<version>\S+)\s+"
                        r"\((?P<date>\d{4}-\d\d-\d\d|in development)\)\s*"
                    ),
                    prev,
                    flags=re.I,
                ):
                    rdate: Optional[str] = m["date"]
                    release_date: Optional[date]
                    if rdate is None or rdate.lower() == "in development":
                        release_date = None
                    else:
                        release_date = date.fromisoformat(rdate)
                    sections.append(
                        ChangelogSection(
                            version=m["version"],
                            release_date=release_date,
                            content="",
                        )
                    )
                elif m := DATE_VERSION.fullmatch(prevt := prev.rstrip()):
                    sections.append(
                        ChangelogSection(
                            version=prevt,
                            release_date=datetime.strptime(prevt, "v%Y.%m.%d").date(),
                            content="",
                        )
                    )
                elif prev.strip().lower() == "in development":
                    sections.append(
                        ChangelogSection(
                            version=None,
                            release_date=None,
                            content="",
                        )
                    )
                else:
                    raise ValueError(
                        f'Section header not in "version (date)" format: {prev!r}'
                    )
                prev = None
            elif prev is not None:
                if sections:
                    sections[-1].content += prev
                else:
                    intro += prev
                prev = line
            else:
                prev = line
        if prev is not None:
            if not sections:
                raise ValueError("Changelog is nonempty but lacks headers")
            sections[-1].content += prev
        if sections:
            sections[-1]._end()
        return cls(intro=intro, sections=sections)

    def dump(self, fp: IO[str]) -> None:
        print(self, file=fp, end="")

    def __str__(self) -> str:
        if self.sections:
            if any("\n\n" in sect.content for sect in self.sections):
                sep = "\n\n\n"
            else:
                sep = "\n\n"
            return self.intro + sep.join(map(str, self.sections)) + "\n"
        else:
            return self.intro


@dataclass
class ChangelogSection:
    # If `version` is unset, then `release_date` should be unset as well; this
    # denotes a section header of just "In Development"
    version: Optional[str]
    release_date: Optional[date]  # None = "in development"
    content: str  # has trailing newlines stripped

    def __str__(self) -> str:
        if self.version is None:
            header = "In Development"
        elif DATE_VERSION.fullmatch(self.version):
            header = self.version
        else:
            if self.release_date is None:
                rdate = "in development"
            else:
                rdate = str(self.release_date)
            header = f"{self.version} ({rdate})"
        return (
            header
            + "\n"
            + "-" * len(header)
            + (f"\n{self.content}" if self.content else "")
        )

    def _end(self) -> None:
        self.content = self.content.rstrip("\r\n")
