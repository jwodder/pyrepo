#!/usr/bin/python3
### Replace with a customized <https://pypi.python.org/pypi/zest.releaser>?
### TODO: Try to give this some level of idempotence
### TODO: Echo a description of each step before it's run?
__python_requires__ = '~= 3.5'
__requires__ = ['requests ~= 2.5']
import os
import os.path
import re
from   shutil     import rmtree
from   subprocess import CalledProcessError, check_output, run
import sys
from   tempfile   import NamedTemporaryFile
import requests

GPG = 'gpg2'
# gpg2 automatically & implicitly uses gpg-agent to obviate the need to keep
# entering one's password.

def main():
    # User has to do these parts emself:
    #0. Merge into `master`
    #1. Update `__version__`
    #2. Update CHANGELOG
    #3. First release: Set repostatus to "Active" and "Development Status"
    #   classifier to "Beta" or higher
    #4. First release: Replace "work-in-progress" GitHub topic with
    #   "available-on-pypi"

    ### Add prompts confirming that the user did all these?

    # GPG_TTY has to be set so that GPG can be run through Git.
    os.environ['GPG_TTY'] = os.ttyname(0)

    # Use `sys.executable` (Python 3) for the initial check because it should
    # be able to handle anything remotely sensible
    if 'Programming Language :: Python :: 3' in \
            readcmd(sys.executable, 'setup.py', '--classifiers').splitlines():
        PYTHON = 'python3'
    else:
        PYTHON = 'python2'

    runcmd(PYTHON, 'setup.py', 'check', '-rms')

    ### TODO: Run tox (and `sdist bdist_wheel`?) around here?

    NAME = readcmd(PYTHON, 'setup.py', '--name')
    VERSION = readcmd(PYTHON, 'setup.py', '--version')

    origin_url = readcmd('git', 'remote', 'get-url', 'origin')
    m = re.fullmatch(
        '(?:https://|git@)github\.com[:/]([^/]+)/([^/]+)\.git',
        origin_url,
        flags=re.I,
    )
    if not m:
        sys.exit('Could not parse remote Git URL: ' + repr(origin_url))
    owner, repo = m.groups()

    with NamedTemporaryFile(mode='w+') as tmplate:
        ### TODO: Try to take default commit message from CHANGELOG / include
        ### CHANGELOG section in template
        tmplate.write('''\
v{} — INSERT SHORT DESCRIPTION HERE

INSERT LONG DESCRIPTION HERE (optional)

# Write in Markdown.
# The first line will be used as the release name.
# The rest will be used as the release body.
'''.format(VERSION))
        tmplate.flush()
        runcmd('git', 'commit', '--template', tmplate.name)
            # Why doesn't this accept '-'?

    ### TODO: Add a confirmation step here

    runcmd(
        'git',
        '-c', 'gpg.program=' + GPG,
        'tag',
        '-s',
        '-m', 'Version ' + VERSION,
        'v' + VERSION,
    )

    runcmd('git', 'push', '--follow-tags')

    subject, body = readcmd(
        'git', 'show', '-s', '--format=%s%x00%b', 'v' + VERSION + '^{commit}',
    ).split('\0', 1)
    requests.post(
        # Authenticate via ~/.netrc
        'https://api.github.com/repos/{}/{}/releases'.format(owner, repo),
        json={
            "tag_name": 'v' + VERSION,
            "name": subject,
            "body": body.strip(),
            "draft": False,
        },
    ).raise_for_status()

    rmtree('dist/', ignore_errors=True)  # To keep things simple
    ### TODO: Suppress output unless an error occurs?
    runcmd(PYTHON, 'setup.py', 'sdist', 'bdist_wheel')

    ### TODO: Add a "confirmation step" here? (Open a shell and abort if it
    ### returns nonzero)

    relfiles = []
    for distfile in os.listdir('dist'):
        distfile = os.path.join('dist', distfile)
        relfiles.append(distfile)
        runcmd(GPG, '--detach-sign', '-a', distfile)
        ### TODO: Use the --sign option to `twine upload` instead?
        relfiles.append(distfile + '.asc')
    ### TODO: Ensure that this always uploads the wheel first?
    runcmd('twine', 'upload', *relfiles)

    #runcms(
    #    'dropbox_uploader',
    #    'upload',
    #    *relfiles,
    #    'Code/Releases/Python/' + NAME + '/',
    #)

    # User:
    # - Make the version docs "active" on Readthedocs
    # - Set `__version__` to the next version number plus `.dev1`
    # - Add new section to top of CHANGELOG

def runcmd(*args):
    r = run(args)
    if r.returncode != 0:
        sys.exit(r.returncode)

def readcmd(*args):
    try:
        return check_output(args, universal_newlines=True).strip()
    except CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == '__main__':
    main()
