# TODO:
# - Try to give this some level of idempotence
# - Add options/individual commands for doing each release step separately

# External dependencies:
# - dropbox_uploader (including OAuth configuration)
# - git (including push access to repository)
# - $GPG (including a key usable for signing)
# - PyPI credentials for twine
# - GitHub OAuth token in config

# Notable assumptions made by this code:
# - There is no CHANGELOG file until after the initial release has been made.
# - The version is set as `__version__` in `packagename/__init__.py` or
#   `packagename.py`.

import logging
from   mimetypes         import add_type, guess_type
import os
import os.path
import re
import sys
from   tempfile          import NamedTemporaryFile
import time
import attr
import click
from   in_place          import InPlace
from   packaging.version import Version
from   uritemplate       import expand
from   ..changelog       import Changelog, ChangelogSection
from   ..gh              import ACCEPT, GitHub
from   ..inspecting      import InvalidProjectError, get_commit_years
from   ..project         import Project
from   ..util            import ensure_license_years, optional, \
                                    read_paragraphs, readcmd, runcmd, \
                                    update_years2str

log = logging.getLogger(__name__)

GPG = 'gpg'
# This must point to gpg version 2 or higher, which automatically & implicitly
# uses gpg-agent to obviate the need to keep entering one's password.

DROPBOX_UPLOAD_DIR = '/Code/Releases/Python/{name}/'

ACTIVE_BADGE = '''\
.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.
'''

TOPICS_ACCEPT = f'application/vnd.github.mercy-preview,{ACCEPT}'

@attr.s
class Releaser:
    project     = attr.ib()
    version     = attr.ib()
    ghrepo      = attr.ib()
    tox         = attr.ib()
    sign_assets = attr.ib()
    assets      = attr.ib(factory=list)
    assets_asc  = attr.ib(factory=list)

    @classmethod
    def from_project(cls, project, version=None, gh=None, tox=False,
                     sign_assets=False):
        if version is None:
            # Remove prerelease & dev release from __version__
            ### TODO: Just use Version.base_version instead?
            version = re.sub(r'(a|b|rc)\d+|\.dev\d+', '', project.version)
        else:
            version = version.lstrip("v")
        if gh is None:
            gh = GitHub()
        return cls(
            project     = project,
            version     = version,
            ghrepo      = gh.repos[project.github_user][project.repo_name],
            tox         = tox,
            sign_assets = sign_assets,
        )

    def run(self):
        self.end_dev()
        if self.tox:
            self.tox_check()
        self.build(sign_assets=self.sign_assets)
        self.twine_check()
        self.commit_version()
        self.mkghrelease()
        self.upload()
        self.begin_dev()

    def tox_check(self):  # Idempotent
        if (self.project.directory / 'tox.ini').exists():
            log.info('Running tox ...')
            runcmd('tox', cwd=self.project.directory)

    def twine_check(self):  # Idempotent
        log.info('Running twine check ...')
        assert self.assets, 'Nothing to check'
        runcmd(sys.executable, '-m', 'twine', 'check', *self.assets)

    def commit_version(self):  ### Not idempotent
        log.info('Committing & tagging ...')
        # We need to create a temporary file instead of just passing the commit
        # message on stdin because `git commit`'s `--template` option doesn't
        # support reading from stdin.
        with NamedTemporaryFile(mode='w+', encoding='utf-8') as tmplate:
            # When using `--template`, Git requires the user to make *some*
            # change to the commit message or it'll abort the commit, so add in
            # a line to delete:
            print('DELETE THIS LINE', file=tmplate)
            print(file=tmplate)
            chlog = self.project.get_changelog()
            if chlog and chlog.sections:
                print(f'v{self.version} — INSERT SHORT DESCRIPTION HERE',
                      file=tmplate)
                print(file=tmplate)
                print('INSERT LONG DESCRIPTION HERE (optional)', file=tmplate)
                print(file=tmplate)
                print('CHANGELOG:', file=tmplate)
                print(file=tmplate)
                print(chlog.sections[0].content, file=tmplate)
            else:
                print(f'v{self.version} — Initial release', file=tmplate)
            print(file=tmplate)
            print('# Write in Markdown.', file=tmplate)
            print('# The first line will be used as the release name.',
                  file=tmplate)
            print('# The rest will be used as the release body.', file=tmplate)
            tmplate.flush()
            runcmd('git', 'commit', '-a', '-v', '--template', tmplate.name,
                   cwd=self.project.directory)
        runcmd(
            'git',
            '-c', 'gpg.program=' + GPG,
            'tag',
            '-s',
            '-m', 'Version ' + self.version,
            'v' + self.version,
            cwd=self.project.directory,
        )
        runcmd('git', 'push', '--follow-tags', cwd=self.project.directory)

    def mkghrelease(self):  ### Not idempotent
        log.info('Creating GitHub release ...')
        subject, body = readcmd(
            'git', 'show', '-s', '--format=%s%x00%b',
            'v' + self.version + '^{commit}',
            cwd=self.project.directory,
        ).split('\0', 1)
        reldata = self.ghrepo.releases.post(json={
            "tag_name": 'v' + self.version,
            "name": subject,
            "body": body.strip(),  ### TODO: Remove line wrapping?
            "draft": False,
        })
        self.release_upload_url = reldata["upload_url"]

    def build(self, sign_assets=False):  ### Not idempotent
        log.info('Building artifacts ...')
        self.project.make(clean=True)
        self.assets = []
        self.assets_asc = []
        for distfile in (self.project.directory / "dist").iterdir():
            self.assets.append(str(distfile))
            if sign_assets:
                runcmd(GPG, '--detach-sign', '-a', str(distfile))
                self.assets_asc.append(str(distfile) + '.asc')

    def upload(self):
        log.info('Uploading artifacts ...')
        assert self.assets, 'Nothing to upload'
        self.upload_pypi()
        self.upload_dropbox()
        self.upload_github()

    def upload_pypi(self):  # Idempotent
        log.info('Uploading artifacts to PyPI ...')
        runcmd(
            sys.executable,
            '-m',
            'twine',
            'upload',
            '--skip-existing',
            *(self.assets + self.assets_asc),
        )

    def upload_dropbox(self):  # Idempotent
        log.info('Uploading artifacts to Dropbox ...')
        runcmd(
            'dropbox_uploader',
            'upload',
            *(self.assets + self.assets_asc),
            DROPBOX_UPLOAD_DIR.format(name=self.project.name),
        )

    def upload_github(self):  ### Not idempotent
        log.info('Uploading artifacts to GitHub release ...')
        assert getattr(self, 'release_upload_url', None) is not None, \
            "Cannot upload to GitHub before creating release"
        for asset in self.assets:
            name = os.path.basename(asset)
            url = expand(self.release_upload_url, name=name, label=None)
            with open(asset, 'rb') as fp:
                self.ghrepo[url].post(
                    headers={"Content-Type": mime_type(name)},
                    data=fp.read(),
                )

    def begin_dev(self):  # Not idempotent
        log.info('Preparing for work on next version ...')
        # Set __version__ to the next version number plus ".dev1"
        old_version = self.project.version
        new_version = next_version(old_version)
        self.project.set_version(new_version + '.dev1')
        # Add new section to top of CHANGELOGs
        new_sect = ChangelogSection(
            version = 'v' + new_version,
            date    = 'in development',
            content = '',
        )
        for docs in (False, True):
            if docs:
                if not (self.project.directory / 'docs').exists():
                    continue
                log.info('Adding new section to docs/changelog.rst ...')
            else:
                log.info('Adding new section to CHANGELOG ...')
            chlog = self.project.get_changelog(docs=docs)
            if chlog and chlog.sections:
                chlog.sections.insert(0, new_sect)
            else:
                chlog = Changelog(
                    intro='Changelog\n=========\n\n' if docs else '',
                    sections=[
                        new_sect,
                        ChangelogSection(
                            version = 'v' + old_version,
                            date    = today(),
                            content = 'Initial release',
                        ),
                    ],
                )
            self.project.set_changelog(chlog, docs=docs)

    def end_dev(self):  # Idempotent
        log.info('Finalizing version ...')
        self.project.set_version(self.version)
        # Set release date in CHANGELOGs
        for docs in (False, True):
            if docs:
                log.info('Updating docs/changelog.rst ...')
            else:
                log.info('Updating CHANGELOG ...')
            chlog = self.project.get_changelog(docs=docs)
            if chlog and chlog.sections:
                chlog.sections[0].date = today()
                self.project.set_changelog(chlog, docs=docs)
        years = get_commit_years(self.project.directory)
        # Update year ranges in LICENSE
        log.info('Ensuring LICENSE copyright line is up to date ...')
        ensure_license_years(self.project.directory / 'LICENSE', years)
        # Update year ranges in docs/conf.py
        docs_conf = self.project.directory / 'docs' / 'conf.py'
        if docs_conf.exists():
            log.info('Ensuring docs/conf.py copyright is up to date ...')
            with InPlace(docs_conf, mode='t', encoding='utf-8') as fp:
                for line in fp:
                    m = re.match(r'^copyright\s*=\s*[\x27"](\d[-,\d\s]+\d) \w+',
                                 line)
                    if m:
                        line = line[:m.start(1)] \
                             + update_years2str(m.group(1), years) \
                             + line[m.end(1):]
                    print(line, file=fp, end='')
        if self.project.get_changelog() is None:
            # Initial release
            self.end_initial_dev()

    def end_initial_dev(self):  # Idempotent
        # Set repostatus to "Active":
        log.info('Advancing repostatus ...')
        ### TODO: Use the Readme class for this:
        with InPlace(
            self.project.directory / 'README.rst', mode='t', encoding='utf-8',
        ) as fp:
            for para in read_paragraphs(fp):
                if para.splitlines()[0] == (
                    '.. image:: http://www.repostatus.org/badges/latest/wip.svg'
                ):
                    print(ACTIVE_BADGE, file=fp)
                else:
                    print(para, file=fp, end='')
        # Set "Development Status" classifier to "Beta" or higher:
        log.info('Advancing Development Status classifier ...')
        with InPlace(
            self.project.directory / 'setup.cfg', mode='t', encoding='utf-8',
        ) as fp:
            matched = False
            for line in fp:
                if re.match(r'^\s*#?\s*Development Status :: [123] ', line):
                    continue
                elif re.match(r'^\s*#?\s*Development Status :: [4567] ', line) \
                        and not matched:
                    matched = True
                    line = line.replace('#', '', 1)
                print(line, file=fp, end='')
        log.info('Updating GitHub topics ...')
        ### TODO: Check that the repository has topics first?
        self.update_gh_topics(
            add=['available-on-pypi'],
            remove=['work-in-progress'],
        )

    def update_gh_topics(self, add=(), remove=()):
        topics = set(
            self.ghrepo.get(headers={"Accept": TOPICS_ACCEPT})["topics"]
        )
        new_topics = topics.union(add).difference(remove)
        if new_topics != topics:
            self.ghrepo.topics.put(
                headers={"Accept": TOPICS_ACCEPT},
                json={"names": list(new_topics)},
            )


@click.command()
@optional('--tox/--no-tox', help='Run tox before building')
@optional('--sign-assets/--no-sign-assets')
@click.argument('version', required=False)
@click.pass_obj
def cli(obj, version, **options):
    try:
        project = Project.from_directory()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    defaults = obj.defaults['release']
    options = dict(defaults, **options)
    sign_assets = options.get("sign_assets", False)
    tox = options.get("tox", False)
    # GPG_TTY has to be set so that GPG can be run through Git.
    os.environ['GPG_TTY'] = os.ttyname(0)
    add_type('application/zip', '.whl', False)
    Releaser(
        project     = project,
        version     = version,
        gh          = obj.gh,
        tox         = tox,
        sign_assets = sign_assets,
    ).run()

def next_version(v):
    """
    >>> next_version('0.5.0')
    '0.6.0'
    >>> next_version('0.5.1')
    '0.6.0'
    >>> next_version('0.5.0.post1')
    '0.6.0'
    >>> next_version('0.5.1.post1')
    '0.6.0'
    >>> next_version('0.5.0a1')
    '0.5.0'
    >>> next_version('0.5.1a1')
    '0.5.1'
    >>> next_version('0.5.0.dev1')
    '0.5.0'
    >>> next_version('0.5.1.dev1')
    '0.5.1'
    >>> next_version('1!0.5.0')
    '1!0.6.0'
    """
    vobj = Version(v)
    if vobj.is_prerelease:
        return str(vobj.base_version)
    vs = list(vobj.release)
    vs[1] += 1
    vs[2:] = [0] * len(vs[2:])
    s = '.'.join(map(str, vs))
    if vobj.epoch:
        s = f'{vobj.epoch}!{s}'
    return s

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
