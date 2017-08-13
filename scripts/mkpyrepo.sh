#!/bin/bash
# Create a GitHub repository for the Python project in the current directory
# Requires <https://github.com/jwodder/ghutil> and jq
set -ex -o pipefail

# Do this first so that messages about installing setup_requires don't end up
# in $NAME
python3 setup.py check

# Assigning the command substitutions to a variable immediately is the only way
# to make the script fail if they fail; cf.
# <http://unix.stackexchange.com/q/23026/11006>
NAME="$(python3 setup.py --name)"
DESC="$(python3 setup.py --description)"
SSH_URL="$(gh repo new -d "$DESC" "$NAME" | jq -r .ssh_url)"

! git remote | grep -qx origin || git remote rm origin
# `grep -v` won't work here, as that makes grep check if any line != "origin"
git remote add origin "$SSH_URL"
git push -u origin master
