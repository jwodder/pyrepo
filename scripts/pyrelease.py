#!/usr/bin/python3
# TODO:
# - Try to give this some level of idempotence
# - Add options/individual commands for doing each release step separately

__python_requires__ = '~= 3.5'
__requires__ = [
    'attrs ~= 18.1',
    'click ~= 7.0',
    'in_place ~= 0.3.0',
    'requests ~= 2.5',
    'uritemplate ~= 3.0',
]

# External dependencies:
# - dropbox_uploader (including OAuth configuration)
# - git (including push access to repository)
# - $GPG (including a key usable for signing)
# - twine (including PyPI credentials)
# - GitHub credentials stored in ~/.netrc

# Notable assumptions made by this code:
# - There is no CHANGELOG file until after the initial release has been made.
# - The version is set as `__version__` in `packagename/__init__.py` or
#   `packagename.py`.

from   mimetypes   import add_type, guess_type
import os
import os.path
import re
from   shutil      import rmtree
import subprocess
import sys
import time
from   tempfile    import NamedTemporaryFile
import attr
import click
from   in_place    import InPlaceText
import requests
from   uritemplate import expand

GPG = 'gpg2'
# gpg2 automatically & implicitly uses gpg-agent to obviate the need to keep
# entering one's password.

SIGN_ASSETS = True

CHECK_TOX = False

DROPBOX_UPLOAD_DIR = '/Code/Releases/Python/{name}/'

CHANGELOG_NAMES = ('CHANGELOG.md', 'CHANGELOG.rst')

ACTIVE_BADGE = '''\
.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.
'''

@attr.s
class Project:
    directory = attr.ib()
    name      = attr.ib()
    _version  = attr.ib()
    python    = attr.ib()
    gh_owner  = attr.ib()
    gh_repo   = attr.ib()
    assets    = attr.ib(factory=list)

    @classmethod
    def from_directory(cls, directory=os.curdir):
        # Use `sys.executable` (Python 3) for the initial check because it
        # should be able to handle anything remotely sensible
        if 'Programming Language :: Python :: 3' in readcmd(
            sys.executable, 'setup.py', '--classifiers', cwd=directory,
        ).splitlines():
            python = 'python3'
        else:
            python = 'python2'
        origin_url = readcmd('git', 'remote', 'get-url', 'origin',
                             cwd=directory)
        m = re.fullmatch(
            r'(?:https://|git@)github\.com[:/]([^/]+)/([^/]+)\.git',
            origin_url,
            flags=re.I,
        )
        if not m:
            raise ValueError('Could not parse remote Git URL: '
                             + repr(origin_url))
        owner, repo = m.groups()
        return cls(
            directory = directory,
            python    = python,
            name      = readcmd(python,'setup.py','--name', cwd=directory),
            # attrs strips leading underscores from variable names for __init__
            # arguments:
            version   = readcmd(python,'setup.py','--version', cwd=directory),
            gh_owner  = owner,
            gh_repo   = repo,
        )

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        self.log('Updating __version__ string ...')
        import_name = self.name.replace('-', '_').replace('.', '_')
        initfile = os.path.join(self.directory, import_name + '.py')
        if not os.path.exists(initfile):
            initfile = os.path.join(self.directory, import_name, '__init__.py')
        with InPlaceText(initfile) as fp:
            for line in fp:
                m = re.match(r'^__version__\s*=', line)
                if m:
                    line = m.group(0) + ' ' + repr(version) + '\n'
                print(line, file=fp, end='')
        self._version = version

    @property
    def changelog(self):
        for fname in CHANGELOG_NAMES:
            try:
                with open(os.path.join(self.directory, fname)) as fp:
                    return Changelog.load(fp)
            except FileNotFoundError:
                continue
        return None

    @changelog.setter
    def changelog(self, value):
        for fname in CHANGELOG_NAMES:
            fpath = os.path.join(self.directory, fname)
            if os.path.exists(fpath):
                if value is None:
                    os.remove(fpath)
                else:
                    with open(fpath, 'w') as fp:
                        print(value, file=fp)
                return
        if value is not None:
            fpath = os.path.join(self.directory, CHANGELOG_NAMES[0])
            with open(fpath, 'w') as fp:
                print(value, file=fp)

    @property
    def ghapi_url(self):
        return 'https://api.github.com/repos/{0.gh_owner}/{0.gh_repo}'\
               .format(self)

    def log(self, s):
        click.secho(s, bold=True)

    def check(self):  # Idempotent
        self.log('Running checks ...')
        if CHECK_TOX and \
                os.path.exists(os.path.join(self.directory), 'tox.ini'):
            runcmd('tox', cwd=self.directory)
        runcmd(self.python, 'setup.py', 'check', '-rms', cwd=self.directory)

    def commit_version(self):  ### Not idempotent
        self.log('Commiting & tagging ...')
        # We need to create a temporary file instead of just passing the commit
        # message on stdin because `git commit`'s `--template` option doesn't
        # support reading from stdin.
        with NamedTemporaryFile(mode='w+') as tmplate:
            # When using `--template`, Git requires the user to make *some*
            # change to the commit message or it'll abort the commit, so add in
            # a line to delete:
            print('DELETE THIS LINE', file=tmplate)
            print(file=tmplate)
            chlog = self.changelog
            if chlog:
                print('v{} — INSERT SHORT DESCRIPTION HERE'.format(self.version),
                      file=tmplate)
                print(file=tmplate)
                print('INSERT LONG DESCRIPTION HERE (optional)', file=tmplate)
                print(file=tmplate)
                print('CHANGELOG:', file=tmplate)
                print(file=tmplate)
                print(chlog.sections[0].content, file=tmplate)
            else:
                print('v{} — Initial release'.format(self.version),
                      file=tmplate)
            print(file=tmplate)
            print('# Write in Markdown.', file=tmplate)
            print('# The first line will be used as the release name.',
                  file=tmplate)
            print('# The rest will be used as the release body.', file=tmplate)
            tmplate.flush()
            runcmd('git', 'commit', '-a', '-v', '--template', tmplate.name,
                   cwd=self.directory)
        runcmd(
            'git',
            '-c', 'gpg.program=' + GPG,
            'tag',
            '-s',
            '-m', 'Version ' + self.version,
            'v' + self.version,
            cwd=self.directory,
        )
        runcmd('git', 'push', '--follow-tags', cwd=self.directory)

    def mkghrelease(self):  ### Not idempotent
        self.log('Creating GitHub release ...')
        subject, body = readcmd(
            'git', 'show', '-s', '--format=%s%x00%b',
            'v' + self.version + '^{commit}',
            cwd=self.directory,
        ).split('\0', 1)
        r = requests.post(
            # Authenticate via ~/.netrc
            self.ghapi_url + '/releases',
            json={
                "tag_name": 'v' + self.version,
                "name": subject,
                "body": body.strip(),  ### TODO: Remove line wrapping?
                "draft": False,
            },
        )
        r.raise_for_status()
        self.release_upload_url = r.json()["upload_url"]

    def build(self):  ### Not idempotent
        self.log('Building artifacts ...')
        distdir = os.path.join(self.directory, 'dist')
        rmtree(distdir, ignore_errors=True)  # To keep things simple
        runcmd(self.python, 'setup.py', '-q', 'sdist', 'bdist_wheel',
               cwd=self.directory)
        for distfile in os.listdir(distdir):
            distfile = os.path.join(distdir, distfile)
            self.assets.append(distfile)
            if SIGN_ASSETS:
                runcmd(GPG, '--detach-sign', '-a', distfile)
                self.assets.append(distfile + '.asc')

    def upload(self):
        self.log('Uploading artifacts ...')
        assert self.assets, 'Nothing to upload'
        self.upload_pypi()
        self.upload_dropbox()
        self.upload_github()

    def upload_pypi(self):  # Idempotent
        self.log('Uploading artifacts to PyPI ...')
        runcmd('twine', 'upload', '--skip-existing', *self.assets)

    def upload_dropbox(self):  # Idempotent
        self.log('Uploading artifacts to Dropbox ...')
        runcmd(
            'dropbox_uploader',
            'upload',
            *self.assets,
            DROPBOX_UPLOAD_DIR.format(name=self.name),
        )

    def upload_github(self):  ### Not idempotent
        self.log('Uploading artifacts to GitHub release ...')
        assert getattr(self, 'release_upload_url', None) is not None, \
            "Cannot upload to GitHub before creating release"
        for asset in self.assets:
            if asset.endswith('.asc'):
                continue
            name = os.path.basename(asset)
            with open(asset, 'rb') as fp:
                requests.post(
                    # Authenticate via ~/.netrc
                    expand(self.release_upload_url, name=name, label=None),
                    headers={"Content-Type": mime_type(name)},
                    data=fp.read(),
                ).raise_for_status()

    def begin_dev(self):  # Not idempotent
        self.log('Preparing for work on next version ...')
        # Set __version__ to the next version number plus ".dev1"
        old_version = self.version
        new_version = next_version(old_version)
        self.version = new_version + '.dev1'
        # Add new section to top of CHANGELOG
        self.log('Adding new section to CHANGELOG ...')
        new_sect = ChangelogSection(
            version = new_version,
            date    = 'in development',
            content = '',
        )
        chlog = self.changelog
        if chlog:
            chlog.sections.insert(0, new_sect)
        else:
            chlog = Changelog([
                new_sect,
                ChangelogSection(
                    version = old_version,
                    date    = today(),
                    content = 'Initial release',
                ),
            ])
        self.changelog = chlog

    def end_dev(self):  # Idempotent
        self.log('Finalizing version ...')
        # Remove prerelease & dev release from __version__
        self.version = re.sub(r'(a|b|rc)\d+|\.dev\d+', '', self.version)
        # Set release date in CHANGELOG
        self.log('Updating CHANGELOG ...')
        chlog = self.changelog
        if chlog:
            chlog.sections[0].date = today()
            self.changelog = chlog
        # Update year ranges in LICENSE
        self.log('Ensuring LICENSE copyright line is up to date ...')
        with InPlaceText(os.path.join(self.directory, 'LICENSE')) as fp:
            for line in fp:
                m = re.match(r'^Copyright \(c\) (\d[-,\d\s]+\d) \w+', line)
                if m:
                    line = line[:m.start(1)] + ensure_year(m.group(1)) \
                         + line[m.end(1):]
                print(line, file=fp, end='')
        # Update year ranges in docs/conf.py
        docs_conf = os.path.join(self.directory, 'docs', 'conf.py')
        if os.path.exists(docs_conf):
            self.log('Ensuring docs/conf.py copyright is up to date ...')
            with InPlaceText(docs_conf) as fp:
                for line in fp:
                    m = re.match(r'^copyright\s*=\s*[\x27"](\d[-,\d\s]+\d) \w+', line)
                    if m:
                        line = line[:m.start(1)] + ensure_year(m.group(1)) \
                             + line[m.end(1):]
                    print(line, file=fp, end='')
        if not chlog:
            # Initial release
            self.end_initial_dev()

    def end_initial_dev(self):  # Idempotent
        # Set repostatus to "Active":
        self.log('Advancing repostatus ...')
        with InPlaceText(os.path.join(self.directory, 'README.rst')) as fp:
            for para in read_paragraphs(fp):
                if para.splitlines()[0] == '.. image:: http://www.repostatus.org/badges/latest/wip.svg':
                    print(ACTIVE_BADGE + '\n', file=fp)
                else:
                    print(para, file=fp, end='')
        # Set "Development Status" classifier to "Beta" or higher:
        self.log('Advancing Development Status classifier ...')
        with InPlaceText(os.path.join(self.directory, 'setup.cfg')) as fp:
            matched = False
            for line in fp:
                if re.match(r'^\s*#?\s*Development Status :: [123] ', line):
                    continue
                elif re.match(r'^\s*#?\s*Development Status :: [4567] ', line) \
                        and not matched:
                    matched = True
                    line = line.replace('#', '', 1)
                print(line, file=fp, end='')
        self.log('Updating GitHub topics ...')
        ### TODO: Check that the repository has topics first?
        self.update_gh_topics(
            add=['available-on-pypi'],
            remove=['work-in-progress'],
        )

    def update_gh_topics(self, add=(), remove=()):
        r = requests.get(
            self.ghapi_url,
            headers={"Accept": 'application/vnd.github.mercy-preview'},
        )
        r.raise_for_status()
        topics = set(r.json()["topics"])
        new_topics = topics.union(add).difference(remove)
        if new_topics != topics:
            requests.put(
                self.ghapi_url + '/topics',
                headers={"Accept": 'application/vnd.github.mercy-preview'},
                json={"names": list(new_topics)},
            ).raise_for_status()


class Changelog:
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
            s += ' ({})'.format(self.date)
        return s + '\n' + '-' * len(s) \
                 + ('\n' + self.content if self.content else '')

    def _end(self):
        self.content = self.content.rstrip('\r\n')


def main():
    # GPG_TTY has to be set so that GPG can be run through Git.
    os.environ['GPG_TTY'] = os.ttyname(0)
    add_type('application/zip', '.whl', False)
    proj = Project.from_directory()
    proj.end_dev()
    proj.check()
    ### TODO: Build assets at this point?
    proj.commit_version()
    proj.mkghrelease()
    proj.build()
    proj.upload()
    proj.begin_dev()
    ### Make the version docs "active" on Readthedocs

def runcmd(*args, **kwargs):
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        sys.exit(r.returncode)

def readcmd(*args, **kwargs):
    try:
        return subprocess.check_output(args, universal_newlines=True, **kwargs)\
                         .strip()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

def next_version(v):
    vs = list(map(int, v.split('.')))
    vs[1] += 1
    return '.'.join(map(str, vs))

def today():
    return time.strftime('%Y-%m-%d')

def mime_type(filename):
    """
    Like `mimetypes.guess_type()`, except that if the file is compressed, the
    MIME type for the compression is returned
    """
    mtype, encoding = guess_type(filename, False)
    if encoding is None:
        return mtype or 'application/octet-stream'
    elif encoding == 'gzip':
        # application/gzip is defined by RFC 6713
        return 'application/gzip'
        # Note that there is a "+gzip" MIME structured syntax suffix specified
        # in an RFC draft that may one day mean the correct code is:
        #return mtype + '+gzip'
    else:
        return 'application/x-' + encoding

def is_blank(line):
    return line in ('\n', '\r\n')

def read_paragraphs(fp):
    para = []
    for line in fp:
        if not is_blank(line) and para and is_blank(para[-1]):
            yield ''.join(para)
            para = [line]
        else:
            para.append(line)
    if para:
        yield ''.join(para)

def ensure_year(year_str, year=None):
    """
    Given a string of years of the form ``"2014, 2016-2017"``, update the
    string if necessary to include the given year (default: the current year).
    The years in the string must be ascending order and must not include any
    future years.

    >>> ensure_year('2015', 2015)
    '2015'
    >>> ensure_year('2015', 2016)
    '2015-2016'
    >>> ensure_year('2015', 2017)
    '2015, 2017'
    >>> ensure_year('2014-2015', 2016)
    '2014-2016'
    >>> ensure_year('2013, 2015', 2016)
    '2013, 2015-2016'
    """
    if year is None:
        year = time.localtime().tm_year
    if not re.search(r'(^|[-,]\s*){}$'.format(year), year_str):
        m = re.search(r'(^|[-,]\s*){}$'.format(year-1), year_str)
        if m:
            if m.group(1).startswith('-'):
                year_str = year_str[:m.end(1)] + str(year)
            else:
                year_str += '-{}'.format(year)
        else:
            year_str += ', {}'.format(year)
    return year_str

if __name__ == '__main__':
    main()
