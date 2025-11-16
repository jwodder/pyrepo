from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any, TextIO
from linesep import read_paragraphs

ParserState = Enum(
    "ParserState", "START BADGES POST_LINKS POST_CONTENTS INTRO SECTIONS"
)

HEADER_LINK_RGX = r"`(?P<label>[^`<>]+) <(?P<url>[^>]+)>`_"

# Technically, this is the regex for a simple reference name; actual
# substitution text can apparently be any text that doesn't begin or end with
# whitespace, but I don't want to try to support parsing that.
SUBST_TEXT_RGX = r"[A-Za-z0-9](?:[-_.:+]?[A-Za-z0-9])*"

IMAGE_START_CRGX = re.compile(
    rf"\.\. \|(?P<tag>{SUBST_TEXT_RGX})\| image:: (?P<href>\S+)$", flags=re.M
)


@dataclass
class Readme:
    """
    See <https://github.com/jwodder/pyrepo/wiki/README-Format> for a
    description of the format parsed & emitted by this class
    """

    badge_tags: list[str]
    badges: list[Image]
    header_links: list[dict]
    contents: bool
    introduction: str | None
    sections: list[Section]

    @classmethod
    def load(cls, fp: TextIO) -> Readme:
        state = ParserState.START
        badges: list[Image] = []
        badge_tags: list[str] = []
        badge_tags_set: set[str] = set()
        seen_badge_tags: set[str] = set()
        header_links: list[dict] = []
        contents = False
        introduction = ""
        sections: list[Section] = []
        section_name: str | None = None
        section_body: str | None = None
        for para in read_paragraphs(fp):
            if state == ParserState.START and re.fullmatch(
                rf"\|{SUBST_TEXT_RGX}\|(?:\s+\|{SUBST_TEXT_RGX}\|)*\s*", para
            ):
                badge_tags = [subst.strip("|") for subst in para.strip().split()]
                badge_tags_set = set(badge_tags)
                state = ParserState.BADGES
            elif state in (ParserState.START, ParserState.BADGES):
                if IMAGE_START_CRGX.match(para):
                    img = Image.parse(para)
                    if img.tag not in badge_tags_set:
                        raise ValueError(f"Unexpected image subsitution: |{img.tag}|")
                    seen_badge_tags.add(img.tag)
                    badges.append(img)
                    state = ParserState.BADGES
                elif re.match(HEADER_LINK_RGX, para):
                    if unseen := badge_tags_set - seen_badge_tags:
                        raise ValueError(
                            "Undefined image substitutions: "
                            + " ".join(f"|{t}|" for t in sorted(unseen))
                        )
                    for hlink in re.split(r"^\|", para.strip(), flags=re.M):
                        if m := re.fullmatch(HEADER_LINK_RGX, hlink.strip()):
                            header_links.append(m.groupdict())
                        else:
                            raise ValueError(f"Invalid header link: {hlink!r}")
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
            badge_tags=badge_tags,
            badges=badges,
            header_links=header_links,
            contents=contents,
            introduction=introduction.strip() or None,
            sections=sections,
        )

    def for_json(self) -> dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        s = ""
        if self.badge_tags:
            s += " ".join(f"|{t}|" for t in self.badge_tags) + "\n\n"
        for b in self.badges:
            s += f"{b}\n\n"
        if self.header_links:
            s += "\n| ".join(map("`{label} <{url}>`_".format_map, self.header_links))
        if self.contents:
            s += "\n\n.. contents::\n    :backlinks: top"
        if self.introduction is not None:
            s += f"\n\n{self.introduction}"
        for i, sect in enumerate(self.sections):
            if i or self.introduction:
                s += "\n"
            s += f'\n\n{sect.name}\n{"=" * len(sect.name)}\n{sect.body}'
        return s + "\n"


@dataclass
class Image:
    tag: str
    href: str
    target: str | None
    alt: str | None

    @classmethod
    def parse(cls, s: str) -> Image:
        if not (m := IMAGE_START_CRGX.match(s)):
            raise ValueError(f"Not an RST image: {s!r}")
        tag = m["tag"]
        href = m["href"]
        lines = s.splitlines(keepends=True)
        options: dict[str, str | None] = {
            "target": None,
            "alt": None,
        }
        opt_name: str | None = None
        opt_value: str | None = None
        for ln in lines[1:]:
            if m := re.match(r"^\s*:(\w+):\s*", ln):
                label = m[1]
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
        return cls(tag=tag, href=href, target=options["target"], alt=options["alt"])

    def __str__(self) -> str:
        s = f".. |{self.tag}| image:: {self.href}"
        if self.target is not None:
            s += f"\n    :target: {self.target}"
        if self.alt is not None:
            s += f"\n    :alt: {self.alt}"
        return s


@dataclass
class Section:
    name: str
    body: str


def is_section_start(para: str) -> bool:
    lines = para.splitlines()
    return len(lines) >= 2 and lines[1] == "=" * len(lines[0])
