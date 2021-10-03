import re
from typing import IO, List, Optional
from pydantic import BaseModel


class ChangelogSection(BaseModel):
    version: str
    date: str
    content: str  # has trailing newlines stripped

    def __str__(self) -> str:
        s = self.version
        if self.date is not None:
            s += f" ({self.date})"
        return s + "\n" + "-" * len(s) + ("\n" + self.content if self.content else "")

    def _end(self) -> None:
        self.content = self.content.rstrip("\r\n")


class Changelog(BaseModel):
    """
    See <https://github.com/jwodder/pyrepo/wiki/CHANGELOG-Format> for a
    description of the format parsed & emitted by this class
    """

    intro: str
    sections: List[ChangelogSection]

    @classmethod
    def load(cls, fp: IO[str]) -> "Changelog":
        intro = ""
        prev: Optional[str] = None
        sections: List[ChangelogSection] = []
        for line in fp:
            if re.match(r"^---+$", line):
                if sections:
                    sections[-1]._end()
                if prev is None:
                    raise ValueError("File begins with hrule")
                if m := re.match(r"^(?P<version>\S+)\s+\((?P<date>.+)\)$", prev):
                    sections.append(
                        ChangelogSection(
                            version=m["version"],
                            date=m["date"],
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

    def for_json(self) -> dict:
        return self.dict()
