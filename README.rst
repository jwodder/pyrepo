.. image:: http://www.repostatus.org/badges/latest/wip.svg
    :target: http://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

.. image:: https://github.com/jwodder/pyrepo/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/pyrepo/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/pyrepo/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/pyrepo

.. image:: https://img.shields.io/github/license/jwodder/pyrepo.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/jwodder

`GitHub <https://github.com/jwodder/pyrepo>`_
| `Issues <https://github.com/jwodder/pyrepo/issues>`_

.. contents::
    :backlinks: top

``jwodder-pyrepo`` is my personal command-line program for managing my Python
package repositories, including generating packaging boilerplate and performing
releases.  It is heavily dependent upon the conventions I use in building &
structuring Python projects, and so it is not suitable for general use.


Installation
============
``jwodder-pyrepo`` requires Python 3.6 or higher to run and `pip
<https://pip.pypa.io>`_ 19.0 or higher to install.  You can install
``jwodder-pyrepo`` and its dependencies by running::

    python3 -m pip install git+https://github.com/jwodder/pyrepo.git


Usage
=====

::

    pyrepo [<global-options>] <command> ...

All ``pyrepo`` commands must either be run from the root of a Python project
directory or else specify the root of such a directory with the ``--chdir``
global option.  Moreover, all commands other than ``pyrepo init`` require that
the project repository have already been set up by previously invoking ``pyrepo
init``.


Global Options
--------------

- ``-c <file>``, ``--config <file>`` — Read configuration from ``<file>``; by
  default, configuration is read from ``~/.config/pyrepo.cfg``

- ``-C <dir>``, ``--chdir <dir>`` — Change to directory ``<dir>`` before taking
  any further actions


Configuration File
------------------

The configuration file (located at ``~/.config/pyrepo.cfg`` by default) is an
INI file with the following sections:

``[auth.github]``
   Contains credentials for interacting with GitHub over v3 of its API.  This
   section should contain a ``token`` option, giving an OAuth2 token to use; if
   not present, API calls to GitHub will fail.

``[options]``
   Sets default values for the options in the ``[options.COMMAND]`` sections

``[options.COMMAND]``
   (where ``COMMAND`` is the name of a ``pyrepo`` subcommand) Sets default
   values for options passed to ``pyrepo COMMAND``

``[pyversions]``
   Contains two options, ``minimum`` and ``maximum``, which give the upper &
   lower bounds of the Python versions to support in a new project.  Both
   values must be of the form ``3.X``.  The options default to the minimum &
   maximum released Python 3 minor versions that have not yet reached
   end-of-life.

Option names are case insensitive and treat hyphens & underscores as equal.


``pyrepo init``
---------------

::

    pyrepo [<global-options>] init [<options>]

Create packaging boilerplate for a new project (i.e., one that does not already
have a ``setup.py``, ``setup.cfg``, or ``pyproject.toml`` file).  The project
must be in a Git repository and already contain Python source code (either one
flat module or else a package containing an ``__init__.py`` file; either layout
may optionally be contained in a ``src/`` directory).  It is recommended to run
this command in a clean Git repository (i.e., one without any pending changes)
so that ``git checkout`` can easily be used to revert the command's effects if
anything goes wrong.

``pyrepo init`` creates the following files if they do not already exist:

- ``.gitignore``
- ``MANIFEST.in``
- ``README.rst``
- ``pyproject.toml``
- ``setup.cfg``

If a ``LICENSE`` file does not exist, one is created; otherwise, the copyright
years in the ``LICENSE`` file are updated.  In both cases, the copyright years
in the ``LICENSE`` will contain the current year and all other years that
commits were made to the Git repository.

A boilerplate docstring and project data variables (``__author__``,
``__author_email__``, ``__license__``, ``__url__``, and ``__version__``) are
also added to the main source file (i.e., the only file if the project
is a flat module, or the ``{{import_name}}/__init__.py`` file otherwise).

If there is a ``requirements.txt`` file and/or a ``__requires__ =
list_of_requirements`` assignment in the main source file, it is used to set
the project's ``install_requires`` in the ``setup.cfg`` and then deleted.  If
both sources of requirements are present, the two lists are combined, erroring
if the same package is given two different requirement specifications.


Options
^^^^^^^

- ``--author <name>`` — Set the name of the project's author

- ``--author-email <email>`` — Set the project's author's e-mail address.  This
  may be either a plain e-mail address or a Jinja2 template defined in terms of
  the variable ``project_name``.

- ``--ci/--no-ci`` — Whether to generate templates for testing with GitHub
  Actions; implies ``--tests``; default: ``--no-ci``

- ``--codecov-user <user>`` — Set the username to use in the Codecov URL added
  to the README when ``--ci`` is given; defaults to the GitHub username

- ``-c <name>``, ``--command <name>`` — If the project defines a command-line
  entry point, use this option to specify the name for the command.  The entry
  point will then be assumed to be at either ``IMPORT_NAME:main`` (if the code
  is a flat module) or ``IMPORT_NAME.__main__:main`` (if the code is a
  package).

- ``-d <text>``, ``--description <text>`` — Set the project's short
  description.  If no description is specified on the command line, the user
  will be prompted for one.

  This option cannot be set via the configuration file.

- ``--docs/--no-docs`` — Whether to generate templates for Sphinx
  documentation; default: ``--no-docs``

- ``--doctests/--no-doctests`` — Whether to include running of doctests in the
  generated testing templates; only has an effect when ``--tests`` is also
  given; default: ``--no-doctests``

- ``--github-user <user>`` — Set the username to use in the project's GitHub
  URL; when not set, the user's GitHub login is retrieved using the GitHub API

- ``-p <name>``, ``--project-name <name>`` — Set the name of the project as it
  will be known on PyPI; defaults to the import name

- ``-P <spec>``, ``--python-requires <spec>`` — Set the project's
  ``python_requires`` value.  ``<spec>`` may be either a PEP 440 version
  specifier (e.g., ``>= 3.3, != 3.4.0``) or a bare ``X.Y`` version (to which
  ``~=`` will be prepended).  When not specified on the command line, this
  value is instead extracted from either a "``# Python <spec>``" comment in
  ``requirements.txt`` or a ``__python_requires__ = '<spec>'`` assignment in
  the main source file; it is an error if these sources have different values.
  If none of these sources are present, ``pyrepo init`` falls back to the value
  of ``python_requires`` in the ``[options.init]`` section of the configuration
  file, which in turn defaults to ``~= pyversions.minimum``.

  - Besides setting ``python_requires``, the value of this option will also be
    applied as a filter to all ``X.Y`` versions from ``pyversions.minimum``
    through ``pyversions.maximum`` in order to determine what Python
    subversions to include classifiers for in ``setup.cfg`` and what
    subversions to test against with tox and CI.

- ``--repo-name <name>`` — The name of the project's repository on GitHub;
  defaults to the project name

- ``--rtfd-name <name>`` — The name of the project's Read the Docs site;
  defaults to the project name

- ``--saythanks-to <user>`` — When this is set, a ``saythanks.io`` badge will
  be included in the generated ``README.rst`` and a "Say Thanks!" entry will be
  included in the ``project_urls``, both pointing to
  ``https://saythanks.io/to/{{saythanks_to}}``

- ``--tests/--no-tests`` — Whether to generate templates for testing with
  pytest and tox; default: ``--no-tests``


``pyrepo inspect``
---------------

::

    pyrepo [<global-options>] inspect

Examine a project repository and output its template variables as a JSON
object.  This command is primarily intended for debugging purposes.


``pyrepo make``
---------------

::

    pyrepo [<global-options>] make [<options>]

Build an sdist and/or wheel for the project.


Options
^^^^^^^

These options cannot be set via the configuration file.

- ``-c``, ``--clean`` — Delete the ``build/`` and ``dist/`` directories from
  the project root before building

- ``--sdist/--no-sdist`` — Whether to build an sdist; default: ``--sdist``

- ``--wheel/--no-wheel`` — Whether to build an sdist; default: ``--wheel``


``pyrepo mkgithub``
-------------------

::

    pyrepo [<global-options>] mkgithub [<options>]

Create a new GitHub repository for the project, set the repository's
description to the project's short description, set the repository's topics to
the project's keywords plus "python", set the local repository's ``origin``
remote to point to the GitHub repository, and push the ``master`` branch to the
repository.


Options
^^^^^^^

- ``--repo-name <name>`` — The name of the new repository; defaults to the
  repository name used in the project's URL.

  This option cannot be set via the configuration file.


``pyrepo release``
------------------

::

    pyrepo [<global-options>] release [<options>]

Create & publish a new release for a project.  This command performs the
following operations in order:

- Remove any prerelease & dev components from ``__version__``
- If a CHANGELOG exists, set the date for the newest version section
- If ``docs/changelog.rst`` exists, set the date for the newest version section
- Update the copyright year ranges in ``LICENSE`` and (if present)
  ``docs/conf.py`` to include all years in which commits were made to the
  repository
- If there is no CHANGELOG file, assume this is the first release and:

  - Update the repostatus badge in the README from "WIP" to "Active"
  - Set the "Development Status" classifier in ``setup.cfg`` to "4 - Beta"
  - Remove the "work-in-progress" topic from the repository on GitHub and add
    the topic "available-on-pypi"

- If the ``--tox`` option is given, run tox, failing if it fails
- Build the sdist & wheel and (if ``--sign-assets`` is given) create detached
  signatures with GPG
- Run ``twine check`` on the sdist & wheel
- Commit all changes made to the repository; the most recent CHANGELOG section
  is included in the commit message template

  - The release can be cancelled at this point by leaving the commit message
    unchanged.

- Tag the commit and sign the tag
- Push the commit & tag to GitHub
- Convert the tag to a release on GitHub, using the commit messsage for the
  name and body
- Upload the build assets to PyPI, Dropbox, and GitHub (as release assets)

  - Detached signatures (if any) are uploaded to PyPI and Dropbox but not
    GitHub

- Prepare for development on the next version by setting ``__version__`` to the
  next minor version number plus ".dev1" and adding a new section to the top of
  the CHANGELOG (creating a CHANGELOG if necessary) and to the top of
  ``docs/changelog.rst`` (creating it if a ``docs`` directory already exists)


Options
^^^^^^^

- ``--tox/--no-tox`` — Whether to run ``tox`` on the project before building;
  default: ``--no-tox``
- ``--sign-assets/--no-sign-assets`` — Whether to created detached PGP
  signatures for the release assets; default: ``--no-sign-assets``


``pyrepo template``
-------------------

::

    pyrepo [<global-options>] template [<options>] <templated-file> ...

Replace the given files with their re-evaluated templates.


Options
^^^^^^^

- ``-o <file>``, ``--outfile <file>`` — Write output to ``<file>`` instead of
  overwriting the file given on the command line.  This option may only be
  used when exactly one argument is given on the command line.

  This option cannot be set via the configuration file.


Restrictions
============
Besides the various assumptions about project layout and formatting,
``jwodder-pyrepo`` does not support the following types of packages:

- packages that are not pure Python
- packages containing more than one root-level module/package
- namespace packages
- (``pyrepo init``) projects that support Python 2
- (``pyrepo release``) projects that only support Python 2
