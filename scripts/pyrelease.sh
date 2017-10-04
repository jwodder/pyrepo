#!/bin/bash
### TODO: Try to give this some level of idempotence
### cf. <https://pypi.python.org/pypi/zest.releaser>?
set -ex -o pipefail
shopt -s lastpipe  # needed for `read`ing from a pipe

# gpg2 automatically & implicitly uses gpg-agent to obviate the need to keep
# entering one's password.
GPG=gpg2
export GPG_TTY=$(tty)  # Has to be exported so GPG can be run through Git

# User has to do these parts emself:
#0. Merge into `master`
#1. Update `__version__`
#2. Update CHANGELOG
#3. First release: Set repostatus to "Active" and "Development Status"
#   classifier to "Beta" or higher

### Add prompts confirming that the user did all these?

####################################

if [ -n "$EXPERIMENTAL" ]
then
    NAME="$($PYTHON setup.py --name)"
    if [ -e "$NAME.py" ]
    then VRS="$NAME.py"
    else VRS="$NAME/__init__.py"
    fi
    sed -i -e '/^__version__/s/\.dev\d+//' "$VRS"  ### Also remove a1 etc. suffixes
    git add "$VRS"

    ### CHANGELOG.*

    ### First release: repostatus and Development Status
fi

####################################

### Run tox and `sdist bdist_wheel` around here?

# Use Python 3 for the initial check because it should be able to handle
# anything remotely sensible
if python3 setup.py --classifiers \
    | grep -Fqx 'Programming Language :: Python :: 3'
then PYTHON=python3
else PYTHON=python2
fi

$PYTHON setup.py check -rms

VERSION="$($PYTHON setup.py --version)"

git remote get-url origin | perl -lne '
    m!^(?:https://|git@)github\.com[:/]([^/]+)/([^/]+)\.git!i and print "$1 $2"
' | read OWNER REPO

### TODO: Try to take default commit message from CHANGELOG

TMPLATE="$(mktemp)"
cat > "$TMPLATE" <<EOT
v$VERSION — INSERT SHORT DESCRIPTION HERE

INSERT LONG DESCRIPTION HERE (optional)

# Write in Markdown.
# The first line will be used as the release name.
# The rest will be used as the release body.
EOT
### TODO: Include CHANGELOG section in template?

git commit --template "$TMPLATE"  # Why doesn't this accept '-'?
rm -f "$TMPLATE"

### TODO: Add a confirmation step here

git -c gpg.program="$GPG" tag -s -m "Version $VERSION" "v$VERSION"
git push --follow-tags

### TODO: gsub doesn't work right when the body contains Unicode characters
### (See <http://github.com/stedolan/jq/issues/1166>); deal with this
### TODO: Remove line wrapping in the body?
git show -s --format=%b "v$VERSION^{commit}" | jq -Rs \
    --arg version "$VERSION" \
    --arg name "$(git show -s --format=%s "v$VERSION^{commit}")" '{
    tag_name: ("v" + $version),
    name: $name,
    body: (gsub("^\\s+|\\s+$"; "")),
    draft: false,
}' | curl -fsSLn -XPOST -d@- https://api.github.com/repos/$OWNER/$REPO/releases

rm -rf dist/  # To keep things simple

### If Python version >= 2.7.9 or >= 3.2:
# $PYTHON setup.py sdist bdist_wheel upload --sign

### Uploading via Twine (or uploading the wheel first?  Research/experiment
### more; cf. <https://github.com/pypa/python-packaging-user-guide/pull/260>)
### seems to be necessary to get the package's dependencies to be listed on its
### PyPI page
###  - It might be the case that testpypi doesn't support showing dependencies
###    no matter what.
###  - Alternatively, maybe PyPI only lists dependencies if the first file
###    uploaded is a .zip sdist or a wheel and not if it's a tarball?

### Else:

$PYTHON setup.py sdist bdist_wheel
### TODO: Add a "confirmation step" here (open a shell and abort if it returns
### nonzero)
for file in dist/*
do "$GPG" --detach-sign -a "$file"
   ### Use the --sign option to `twine upload` instead?
done
### TODO: Ensure that this always uploads the wheel first!
twine upload dist/*

### Upload to Dropbox?

# User:
# - Make the version docs "active" on Readthedocs
# - Set `__version__` to the next version number plus `.dev1`
