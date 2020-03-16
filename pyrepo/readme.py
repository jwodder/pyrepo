from   enum  import Enum
import re
import attr
from   .util import read_paragraphs

ParserState = Enum('ParserState', 'BADGES POST_LINKS POST_CONTENTS INTRO SECTIONS')

HEADER_LINK_RGX = r'`(?P<label>[^`<>]+) <(?P<url>[^>]+)>`_'

IMAGE_START = '.. image:: '

@attr.s
class Readme:
    """
    See <https://github.com/jwodder/pyrepo/wiki/README-Format> for a
    description of the format parsed & emitted by this class
    """
    badges       = attr.ib()
    header_links = attr.ib()
    contents     = attr.ib()
    introduction = attr.ib()
    sections     = attr.ib()

    @classmethod
    def parse(cls, fp):
        state = ParserState.BADGES
        badges = []
        header_links = []
        contents = False
        introduction = ''
        sections = []
        section_name = None
        section_body = None
        for para in read_paragraphs(fp):
            if state == ParserState.BADGES:
                if para.startswith(IMAGE_START):
                    badges.append(Image.parse_string(para))
                elif re.match(HEADER_LINK_RGX, para):
                    for hlink in re.split(r'^\|', para.strip(), flags=re.M):
                        m = re.fullmatch(HEADER_LINK_RGX, hlink.strip())
                        if not m:
                            raise ValueError(f'Invalid header link: {hlink!r}')
                        header_links.append(m.groupdict())
                    state = ParserState.POST_LINKS
                else:
                    raise ValueError(f'Expected image or header links,'
                                     f' found {para.splitlines()[0]!r}')
            elif state == ParserState.POST_LINKS \
                    and para.startswith('.. contents::'):
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
                    section_body = ''.join(lines[2:])
                    state = ParserState.SECTIONS
                else:
                    introduction += para
                    state = ParserState.INTRO
            else:
                assert state == ParserState.SECTIONS
                if is_section_start(para):
                    sections.append({
                        "name": section_name,
                        "body": section_body.rstrip(),
                    })
                    lines = para.splitlines(keepends=True)
                    section_name = lines[0].strip()
                    section_body = ''.join(lines[2:])
                else:
                    section_body += para
        if section_body is not None:
            sections.append({
                "name": section_name,
                "body": section_body.rstrip(),
            })
        return cls(
            badges       = badges,
            header_links = header_links,
            contents     = contents,
            introduction = introduction.strip() or None,
            sections     = sections,
        )

    def __str__(self):
        s = ''
        for b in self.badges:
            s += str(b) + '\n\n'
        if self.header_links:
            s += '\n| '.join(
                map('`{label} <{url}>`_'.format_map, self.header_links)
            )
        if self.contents:
            s += '\n\n.. contents::\n    :backlinks: top'
        if self.introduction is not None:
            s += '\n\n' + self.introduction
        for i, sect in enumerate(self.sections):
            if i or self.introduction:
                s += '\n'
            s += f'\n\n{sect["name"]}\n{"="*len(sect["name"])}\n{sect["body"]}'
        return s + '\n'

    def for_json(self):
        return attr.asdict(self)


@attr.s
class Image:
    href   = attr.ib()
    target = attr.ib()
    alt    = attr.ib()

    @classmethod
    def parse_string(cls, s):
        if not s.startswith(IMAGE_START):
            raise ValueError(f'Not an RST image: {s!r}')
        lines = s.splitlines(keepends=True)
        href = lines[0][len(IMAGE_START):].strip()
        options = {
            "target": None,
            "alt": None,
        }
        opt_name = None
        opt_value = None
        for l in lines[1:]:
            m = re.match(r'^\s*:(\w+):\s*', l)
            if m:
                label = m.group(1)
                if label not in options:
                    raise ValueError(f"Unknown image option: ':{label}:'")
                elif options[label] is not None or label == opt_name:
                    raise ValueError(f"Image has multiple :{label}: options")
                if opt_name is not None:
                    options[opt_name] = opt_value.rstrip()
                opt_name = label
                opt_value = l[m.end():]
            elif opt_name is not None:
                opt_value += l
            elif l.strip() != '':
                raise ValueError(f'Non-option line in image: {l!r}')
        if opt_name is not None:
            options[opt_name] = opt_value.rstrip()
        return cls(href=href, **options)

    def __str__(self):
        s = IMAGE_START + self.href
        if self.target is not None:
            s += '\n    :target: ' + self.target
        if self.alt is not None:
            s += '\n    :alt: ' + self.alt
        return s


def is_section_start(para):
    lines = para.splitlines()
    return len(lines) >= 2 and lines[1] == '=' * len(lines[0])
