import re
import attr

class Changelog:
    """
    See <https://github.com/jwodder/pyrepo/wiki/CHANGELOG-Format> for a
    description of the format parsed & emitted by this class
    """

    def __init__(self, sections):
        self.sections = list(sections)

    @classmethod
    def load(cls, fp):
        prev = None
        sections = []
        for line in fp:
            if re.match(r'^---+$', line):
                if sections:
                    sections[-1]._end()
                if prev is None:
                    raise ValueError('File begins with hrule')
                m = re.match(r'^(?P<version>\S+)\s+\((?P<date>.+)\)$', prev)
                if not m:
                    raise ValueError('Section header not in "version (date)"'
                                     ' format: ' + repr(prev))
                sections.append(ChangelogSection(
                    version = m.group('version'),
                    date    = m.group('date'),
                    content = '',
                ))
                prev = None
            else:
                if prev is not None and sections:
                    sections[-1].content += prev
                prev = line
        if prev is not None:
            if not sections:
                raise ValueError('Changelog is nonempty but lacks headers')
            sections[-1].content += prev
        if sections:
            sections[-1]._end()
        return cls(sections)

    def __str__(self):
        if any('\n\n' in sect.content for sect in self.sections):
            sep = '\n\n\n'
        else:
            sep = '\n\n'
        return sep.join(map(str, self.sections))

    def __bool__(self):
        return bool(self.sections)


@attr.s
class ChangelogSection:
    version = attr.ib()
    date    = attr.ib()
    content = attr.ib()  # has trailing newlines stripped

    def __str__(self):
        s = self.version
        if self.date is not None:
            s += f' ({self.date})'
        return s + '\n' + '-' * len(s) \
                 + ('\n' + self.content if self.content else '')

    def _end(self):
        self.content = self.content.rstrip('\r\n')
