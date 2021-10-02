from enum import Enum
import re
from typing import Dict, List, Optional, TextIO
from linesep import read_paragraphs
from pydantic import BaseModel

ParserState = Enum("ParserState", "BADGES POST_LINKS POST_CONTENTS INTRO SECTIONS")

HEADER_LINK_RGX = r"`(?P<label>[^`<>]+) <(?P<url>[^>]+)>`_"

IMAGE_START = ".. image:: "


class Image(BaseModel):
    href: str
    target: Optional[str]
    alt: Optional[str]

    @classmethod
    def parse_string(cls, s: str) -> "Image":
        if not s.startswith(IMAGE_START):
            raise ValueError(f"Not an RST image: {s!r}")
        lines = s.splitlines(keepends=True)
        href = lines[0][len(IMAGE_START) :].strip()
        options: Dict[str, Optional[str]] = {
            "target": None,
            "alt": None,
        }
        opt_name: Optional[str] = None
        opt_value: Optional[str] = None
        for ln in lines[1:]:
            m = re.match(r"^\s*:(\w+):\s*", ln)
            if m:
                label = m.group(1)
                if label not in options:
                    raise ValueError(f"Unknown image option: ':{label}:'")
                elif options[label] is not None or label == opt_name:
                    raise ValueError(f"Image has multiple :{label}: options")
                if opt_name is not None:
                    assert opt_value is not None
                    options[opt_name] = opt_value.rstrip()
                opt_name = label
                opt_value = ln[m.end() :]
            elif opt_name is not None:
                assert opt_value is not None
                opt_value += ln
            elif ln.strip() != "":
                raise ValueError(f"Non-option line in image: {ln!r}")
        if opt_name is not None:
            assert opt_value is not None
            options[opt_name] = opt_value.rstrip()
        return cls.parse_obj({"href": href, **options})

    def __str__(self) -> str:
        s = IMAGE_START + self.href
        if self.target is not None:
            s += "\n    :target: " + self.target
        if self.alt is not None:
            s += "\n    :alt: " + self.alt
        return s


class Section(BaseModel):
    name: str
    body: str


class Readme(BaseModel):
    """
    See <https://github.com/jwodder/pyrepo/wiki/README-Format> for a
    description of the format parsed & emitted by this class
    """

    badges: List[Image]
    header_links: List[dict]
    contents: bool
    introduction: Optional[str]
    sections: List[Section]

    @classmethod
    def parse(cls, fp: TextIO) -> "Readme":
        state = ParserState.BADGES
        badges: List[Image] = []
        header_links: List[dict] = []
        contents = False
        introduction = ""
        sections: List[Section] = []
        section_name: Optional[str] = None
        section_body: Optional[str] = None
        for para in read_paragraphs(fp):
            if state == ParserState.BADGES:
                if para.startswith(IMAGE_START):
                    badges.append(Image.parse_string(para))
                elif re.match(HEADER_LINK_RGX, para):
                    for hlink in re.split(r"^\|", para.strip(), flags=re.M):
                        m = re.fullmatch(HEADER_LINK_RGX, hlink.strip())
                        if not m:
                            raise ValueError(f"Invalid header link: {hlink!r}")
                        header_links.append(m.groupdict())
                    state = ParserState.POST_LINKS
                else:
                    raise ValueError(
                        f"Expected image or header links,"
                        f" found {para.splitlines()[0]!r}"
                    )
            elif state == ParserState.POST_LINKS and para.startswith(".. contents::"):
                contents = True
                state = ParserState.POST_CONTENTS
            elif state in (
                ParserState.POST_LINKS,
                ParserState.POST_CONTENTS,
                ParserState.INTRO,
            ):
                if is_section_start(para):
                    lines = para.splitlines(keepends=True)
                    section_name = lines[0].strip()
                    section_body = "".join(lines[2:])
                    state = ParserState.SECTIONS
                else:
                    introduction += para
                    state = ParserState.INTRO
            else:
                assert state == ParserState.SECTIONS
                assert section_name is not None
                assert section_body is not None
                if is_section_start(para):
                    sections.append(
                        Section(name=section_name, body=section_body.rstrip())
                    )
                    lines = para.splitlines(keepends=True)
                    section_name = lines[0].strip()
                    section_body = "".join(lines[2:])
                else:
                    section_body += para
        if section_body is not None:
            assert section_name is not None
            sections.append(Section(name=section_name, body=section_body.rstrip()))
        return cls(
            badges=badges,
            header_links=header_links,
            contents=contents,
            introduction=introduction.strip() or None,
            sections=sections,
        )

    def __str__(self) -> str:
        s = ""
        for b in self.badges:
            s += str(b) + "\n\n"
        if self.header_links:
            s += "\n| ".join(map("`{label} <{url}>`_".format_map, self.header_links))
        if self.contents:
            s += "\n\n.. contents::\n    :backlinks: top"
        if self.introduction is not None:
            s += "\n\n" + self.introduction
        for i, sect in enumerate(self.sections):
            if i or self.introduction:
                s += "\n"
            s += f'\n\n{sect.name}\n{"="*len(sect.name)}\n{sect.body}'
        return s + "\n"

    def for_json(self) -> dict:
        return self.dict()


def is_section_start(para: str) -> bool:
    lines = para.splitlines()
    return len(lines) >= 2 and lines[1] == "=" * len(lines[0])
