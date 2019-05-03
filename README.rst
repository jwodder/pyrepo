.. image:: http://www.repostatus.org/badges/latest/wip.svg
    :target: http://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

.. image:: https://travis-ci.org/jwodder/pyrepo.svg?branch=master
    :target: https://travis-ci.org/jwodder/pyrepo

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
<https://pip.pypa.io>`_ 6.0+, `Setuptools <https://setuptools.readthedocs.io>`_
38.6.0+, & `wheel <https://pypi.org/project/wheel>`_ to install.  `Once you
have those
<https://packaging.python.org/tutorials/installing-packages/#ensure-pip-setuptools-and-wheel-are-up-to-date>`_,
you can install ``jwodder-pyrepo`` and its dependencies by running::

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


.. _configuration_file:

Configuration File
------------------

The configuration file (located at ``~/.config/pyrepo.cfg`` by default) is an
INI file with the following sections:

``[auth.github]``
   Contains credentials for interacting with GitHub over v3 of its API.  This
   section may contain either a ``token`` option, giving an OAuth2 token to
   use, or ``username`` and ``password`` options.  If none of these are
   present, the user's credentials for ``api.github.com`` (and
   ``uploads.github.com``, for attaching assets to releases) are expected to be
   set in their ``~/.netrc`` file.

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
have a ``setup.py`` file).  The project must be in a Git repository and already
contain Python source code (either one flat module or else a package containing
an ``__init__.py`` file).  It is recommended to run this command in a clean Git
repository (i.e., one without any pending changes) so that ``git reset`` can
easily be used to revert the command's effects if anything goes wrong.

``pyrepo init`` creates and ``git add``\ s the following files if they do not
already exist:

- ``.gitignore``
- ``MANIFEST.in``
- ``README.rst``
- ``setup.cfg``
- ``setup.py``

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

- ``--codecov-user <user>`` — Set the username to use in the Codecov URL added
  to the README when ``--travis`` is given; defaults to the GitHub username

- ``-c <name>``, ``--command <name>`` — If the project defines a command-line
  entry point, use this option to specify the name for the command.  The entry
  point will then be assumed to be at either ``IMPORT_NAME:main`` (if the code
  is flat module) or ``IMPORT_NAME.__main__:main`` (if the code is a package).

- ``-d <text>``, ``--description <text>`` — Set the project's short
  description.  If no description is specified on the command line, the user
  will be prompted for one.

  This option cannot be set via the configuration file.

- ``--docs``, ``--no-docs`` — Whether to generate templates for Sphinx
  documentation; default: ``--no-docs``

- ``--github-user <user>`` — Set the username to use in the project's GitHub
  URL; when not set, the user's GitHub login is retrieved using the GitHub API

- ``-i <name>``, ``--import-name <name>`` — Specify the import name of the
  Python module or package that the project is built around.  If not specified,
  the current directory is scanned for ``*.py`` and ``*/__init__.py`` files.  A
  project may only contain exactly one module or package.

- ``--importable``, ``--no-importable`` — A project is said to be *importable*
  iff ``from IMPORT_NAME import __version__`` succeeds even when none of the
  project's dependencies have been installed yet; this determines whether
  setuptools will be fetching the project version with a ``setup.cfg`` line of
  ``version = attr:IMPORT_NAME.__version__`` or using boilerplate scanning code
  in ``setup.py`` instead.  By default, a project is assumed to be importable
  iff the project has no requirements or the project is a package containing a
  ``__main__.py`` file (in which case it is assumed that the project is a
  command rather than a library and that ``__init__.py`` imports nothing); use
  these options to explicitly override the assumed importability.

  This option cannot be set via the configuration file.

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
    subversions to test against with tox and Travis.

- ``--repo-name <name>`` — The name of the project's repository on GitHub;
  defaults to the project name

- ``--rtfd-name <name>`` — The name of the project's Read the Docs site;
  defaults to the project name

- ``--saythanks-to <user>`` — When this is set, a ``saythanks.io`` badge will
  be included in the generated ``README.rst`` and a "Say Thanks!" entry will be
  included in the ``project_urls``, both pointing to
  ``https://saythanks.io/to/{{saythanks_to}}``

- ``--tests``, ``--no-tests`` — Whether to generate templates for testing with
  pytest and tox; default: ``--no-tests``

- ``--travis``, ``--no-travis`` — Whether to generate templates for testing
  with Travis; implies ``--tests``; default: ``--no-travis``

- ``--travis-user <user>`` — Set the username to use in the Travis URL added to
  the README when ``--travis`` is given; defaults to the GitHub username


``pyrepo inspect``
---------------

::

    pyrepo [<global-options>] inspect

Examine a project repository and output its template variables as a JSON
object.  This command is primarily intended for debugging purposes.


``pyrepo mkgithub``
-------------------

::

    pyrepo [<global-options>] mkgithub [<options>]

Create a new GitHub repository for the project and push the ``master`` branch
to it.


Options
^^^^^^^

- ``--repo-name <name>`` — The name of the new repository; defaults to the
  project name


``pyrepo release``
------------------

::

    pyrepo [<global-options>] release

Create & publish a new release for a project.  This command performs the
following operations in order:

- Remove any prerelease & dev components from ``__version__``
- If a CHANGELOG exists, set the date for the newest version section
- Update the copyright year ranges in ``LICENSE`` and (if present)
  ``docs/conf.py`` to include the current year
- If there is no CHANGELOG file, assume this is the first release and:

  - Update the repostatus badge in the README from "WIP" to "Active"
  - Set the "Development Status" classifier in ``setup.cfg`` to "4 - Beta"
  - Remove the "work-in-progress" topic from the repository on GitHub and add
    the topic "available-on-pypi"

- Build the sdist & wheel and create detached signatures with GPG
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
- Prepare for development on the next version by setting ``__version__`` to the
  next minor version number plus ".dev1" and adding a new section to the top of
  the CHANGELOG (creating a CHANGELOG if necessary)


Restrictions
============
Besides the various assumptions about project layout and formatting,
``jwodder-pyrepo`` does not support the following types of packages:

- packages that are not pure Python
- packages containing more than one root-level module/package
- namespace packages
- (``pyrepo init``) projects that support Python 2
- (``pyrepo release``) projects that only support Python 2
