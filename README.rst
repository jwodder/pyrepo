.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.

.. image:: https://github.com/jwodder/pyrepo/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/pyrepo/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/pyrepo/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/pyrepo

.. image:: https://img.shields.io/github/license/jwodder/pyrepo.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/pyrepo>`_
| `Issues <https://github.com/jwodder/pyrepo/issues>`_
| `Changelog <https://github.com/jwodder/pyrepo/blob/master/CHANGELOG.md>`_

.. contents::
    :backlinks: top

``jwodder-pyrepo`` is my personal command-line program for managing my Python
package repositories, including generating packaging boilerplate and performing
releases.  It is heavily dependent upon the conventions I use in building &
structuring Python projects (documented in `the repository wiki
<https://github.com/jwodder/pyrepo/wiki>`__), and so it is not suitable for
general use.


Installation
============
``jwodder-pyrepo`` requires Python 3.8 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/pyrepo.git


Usage
=====

::

    pyrepo [<global-options>] <command> ...

All ``pyrepo`` commands other than ``pyrepo init`` must be run inside a Python
project directory (after processing the ``--chdir`` option, if given); the
project root is determined by recursing upwards in search of a
``pyproject.toml`` file.  Moreover, all commands other than ``pyrepo init``
require that the project have already been set up by previously invoking
``pyrepo init``.


Global Options
--------------

-c FILE, --config FILE  Read configuration from ``FILE``; by default,
                        configuration is read from ``~/.config/pyrepo.toml``

-C DIR, --chdir DIR     Change to directory ``DIR`` before taking any further
                        actions

-l LEVEL, --log-level LEVEL
                        Set the `logging level`_ to the given value; default:
                        ``INFO``.  The level can be given as a case-insensitive
                        level name or as a numeric value.

                        This option can be set via the configuration file.

.. _logging level: https://docs.python.org/3/library/logging.html
                   #logging-levels


Configuration File
------------------

The configuration file (located at ``~/.config/pyrepo.toml`` by default) is a
TOML_ file with the following tables:

.. _TOML: https://toml.io

``[auth.github]``
   Contains credentials for interacting with GitHub over v3 of its API.  This
   table should contain a ``token`` option, giving an OAuth2 token to use; if
   not present, API calls to GitHub will fail.

``[options]``
    Sets default values for global options

``[options.COMMAND]``
   (where ``COMMAND`` is the name of a ``pyrepo`` subcommand) Sets default
   values for options passed to ``pyrepo COMMAND``.

Not all options can be configured via the configuration file; see the
documentation for the respective options to find out which can.

Hyphens & underscores are interchangeable in option names in the configuration
file.


``pyrepo init``
---------------

::

    pyrepo [<global-options>] init [<options>] [<directory>]

Create packaging boilerplate for a new project (i.e., one that does not already
have a ``setup.py``, ``setup.cfg``, or ``pyproject.toml`` file) in
``<directory>`` (default: the current directory).  The project must be in a Git
repository and already contain Python source code (either one flat module or
else a package containing an ``__init__.py`` file; either layout may optionally
be contained in a ``src/`` directory).  It is recommended to run this command
in a clean Git repository (i.e., one without any pending changes) so that the
command's effects can easily be reverted should anything go wrong.

``pyrepo init`` moves the code into a ``src/`` directory (if it not in one
already) and creates the following files if they do not already exist:

- ``.gitignore``
- ``.pre-commit-config.yaml``
- ``MANIFEST.in``
- ``README.rst``
- ``pyproject.toml``
- ``setup.cfg``
- ``tox.ini``

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

Finally, ``pre-commit install`` is run, and a message is printed instructing
the user to run ``pre-commit run -a`` after adding new files to the index.


Options
^^^^^^^

All of the following can be set via the configuration file, in the
``[options.init]`` table.

--author NAME           Set the name of the project's author

--author-email EMAIL    Set the project's author's e-mail address.  This may be
                        either a plain e-mail address or a Jinja2 template
                        defined in terms of the variables ``project_name`` and
                        ``import_name``.

--ci, --no-ci           Whether to generate templates for testing with GitHub
                        Actions; implies ``--tests``; default: ``--no-ci``

--codecov-user USER     Set the username to use in the Codecov URL added to the
                        README when ``--ci`` is given; defaults to the GitHub
                        username

-c, --command NAME      If the project defines a command-line entry point, use
                        this option to specify the name for the command.  The
                        entry point will then be assumed to be at either
                        ``IMPORT_NAME:main`` (if the code is a flat module) or
                        ``IMPORT_NAME.__main__:main`` (if the code is a
                        package).

-d TEXT, --description TEXT
                        Set the project's short description.  If no description
                        is specified on the command line, the user will be
                        prompted for one.

--docs, --no-docs       Whether to generate templates for Sphinx documentation;
                        default: ``--no-docs``

--doctests, --no-doctests
                        Whether to include running of doctests in the generated
                        testing templates; only has an effect when ``--tests``
                        is also given; default: ``--no-doctests``

--github-user USER      Set the username to use in the project's GitHub URL;
                        when not set, the user's GitHub login is retrieved
                        using the GitHub API

-p NAME, --project-name NAME
                        Set the name of the project as it will be known on
                        PyPI; defaults to the import name.

                        This can be set to a Jinja2 template defined in terms
                        of the variable ``import_name``.

-P SPEC, --python-requires SPEC
                        Set the project's ``python_requires`` value.  ``SPEC``
                        may be either a PEP 440 version specifier (e.g., ``>=
                        3.3, != 3.4.0``) or a bare ``X.Y`` version (to which
                        ``>=`` will be prepended).  When not specified on the
                        command line, this value is instead extracted from
                        either a "``# Python SPEC``" comment in
                        ``requirements.txt`` or a ``__python_requires__ =
                        'SPEC'`` assignment in the main source file; it is an
                        error if these sources have different values.  If none
                        of these sources are present, ``pyrepo init`` falls
                        back to the value of ``python_requires`` in the
                        ``[options.init]`` table of the configuration file,
                        which in turn defaults to ``>=`` plus the current
                        minimum supported Python series.

                        Besides setting ``python_requires``, the value of this
                        option will also be applied as a filter to all
                        currently-supported Python series in order to determine
                        what Python series to include classifiers for in
                        ``setup.cfg`` and what series to test against with tox
                        and CI.

--repo-name NAME        The name of the project's repository on GitHub;
                        defaults to the project name.

                        This can be set to a Jinja2 template defined in terms
                        of the variables ``project_name`` and ``import_name``.

--rtfd-name NAME        The name of the project's Read the Docs site; defaults
                        to the project name.

                        This can be set to a Jinja2 template defined in terms
                        of the variables ``project_name`` and ``import_name``.

--tests, --no-tests     Whether to generate templates for testing with pytest
                        and tox; default: ``--no-tests``

--typing, --no-typing   Whether to include configuration for type annotations
                        (creating a ``py.typed`` file, adding a ``typing``
                        testenv to ``tox.ini`` if ``--tests`` is set, adding a
                        ``typing`` job to the CI configuration if ``--ci`` is
                        set, etc.); default: ``--no-typing``


``pyrepo add-ci-testenv``
-------------------------

::

    pyrepo [<global-options>] add-ci-testenv <testenv> <python-version>

Configure the GitHub Actions test workflow to include a run of the tox
environment ``<testenv>`` against ``<python-version>``.


``pyrepo add-pyversion``
------------------------

::

    pyrepo [<global-options>] add-pyversion <version> ...

Configure the project to declare support for and test against the given Python
version(s) (which must be given in the form "``X.Y``").

Note that this command will not modify the project's ``python_requires``
setting.  If a given version is out of bounds for ``python_requires``, an error
will result; update ``python_requires`` and try again.


``pyrepo add-typing``
---------------------

::

    pyrepo [<global-options>] add-typing


Add configuration for type annotations and the checking thereof:

- Add a ``py.typed`` file to the Python package (after converting from a flat
  module, if necessary)

- Add a "``Typing :: Typed``" classifier to the project classifiers

- Add a ``mypy`` configuration section to ``setup.cfg``

- Add a ``typing`` testenv to ``tox.ini`` if tests are enabled

- Add a ``typing`` job (run against the lowest supported Python version) to the
  CI configuration if it exists


``pyrepo begin-dev``
--------------------

::

    pyrepo [<global-options>] begin-dev [<options>]

Prepare for development on the next version of a project by setting
``__version__`` to the next minor version number plus ".dev1" and adding a new
section to the top of the CHANGELOG (creating a CHANGELOG if necessary) and to
the top of ``docs/changelog.rst`` (creating it if a ``docs`` directory already
exists).  This is the same behavior as the last step of ``pyrepo release``.

If the project uses versioningit_, the ``__version__`` variable is left alone.

If the project is already in "dev mode", nothing is done.

Options
^^^^^^^

-N, --no-next-version           Do not calculate the next version for the
                                project: set ``__version__`` (if not using
                                versioningit) to the current version plus
                                ".post1" and omit the version from the new
                                CHANGELOG section


``pyrepo drop-pyversion``
-------------------------

::

    pyrepo [<global-options>] drop-pyversion

Configure the project to no longer declare support for or test against the
current lowest supported minor Python version.

It is an error to run this command when the project declares support for only
zero or one minor Python version.


``pyrepo inspect``
------------------

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

-c, --clean             Delete the ``build/`` and ``dist/`` directories from
                        the project root before building

--sdist, --no-sdist     Whether to build an sdist; default: ``--sdist``

--wheel, --no-wheel     Whether to build an sdist; default: ``--wheel``


``pyrepo mkgithub``
-------------------

::

    pyrepo [<global-options>] mkgithub [<options>]

Create a new GitHub repository for the project, set the repository's
description to the project's short description, set the repository's topics to
the project's keywords plus "python", set the local repository's ``origin``
remote to point to the GitHub repository, and push all branches & tags to the
remote.


Options
^^^^^^^

-P, --private           Make the new repository private.

--repo-name NAME        The name of the new repository; defaults to the
                        repository name used in the project's URL.


``pyrepo release``
------------------

::

    pyrepo [<global-options>] release [<options>] [<version>]

Create & publish a new release for a project.  This command performs the
following operations in order:

- If the version for the new release is not specified on the command line, it
  is calculated by removing any prerelease & dev components from the project's
  current version
- If the project does not use versioningit_, set ``__version__`` to the version
  of the new release
- If a CHANGELOG exists, set the date for the newest version section
- If ``docs/changelog.rst`` exists, set the date for the newest version section
- Update the copyright year ranges in ``LICENSE`` and (if present)
  ``docs/conf.py`` to include all years in which commits were made to the
  repository
- If there is no CHANGELOG file, assume this is the first release and:

  - Update the repostatus badge in the README from "WIP" to "Active"
  - If the project does not have a "Private" classifier, remove the
    "work-in-progress" topic from the repository on GitHub and add the topic
    "available-on-pypi"

- If the ``--tox`` option is given, run tox, failing if it fails
- Build the sdist & wheel
- Run ``twine check`` on the sdist & wheel
- Commit all changes made to the repository; the most recent CHANGELOG section
  is included in the commit message template.  The commit is then tagged &
  signed.

  - The release can be cancelled at this point by leaving the commit message
    unchanged.

  - If the project uses ``versioningit``, this step is moved to before building
    the sdist & wheel.

- Push the commit & tag to GitHub
- Convert the tag to a release on GitHub, using the commit message for the name
  and body
- If the project does not have a "Private" classifier, upload the build assets
  to PyPI
- Upload the build assets to GitHub as release assets
- Prepare for development on the next version by setting ``__version__`` to the
  next minor version number plus ".dev1" and adding a new section to the top of
  the CHANGELOG (creating a CHANGELOG if necessary) and to the top of
  ``docs/changelog.rst`` (creating it if a ``docs`` directory already exists)

  If the project uses versioningit_, the ``__version__`` variable is left
  alone.


Options
^^^^^^^

--tox, --no-tox         Whether to run ``tox`` on the project before building;
                        default: ``--no-tox``.

                        This option can be set via the configuration file.

--major                 Set the release's version to the next major version

--minor                 Set the release's version to the next minor version

--micro                 Set the release's version to the next micro/patch
                        version

--post                  Set the release's version to the next post version

--date                  Set the release's version to the current date in
                        ``YYYY.MM.DD`` format


``pyrepo template``
-------------------

::

    pyrepo [<global-options>] template [<options>] <templated-file> ...

Replace the given files with their re-evaluated templates.


Options
^^^^^^^

-o FILE, --outfile FILE
                        Write output to ``<file>`` instead of overwriting the
                        file given on the command line.  This option may only
                        be used when exactly one argument is given on the
                        command line.


``pyrepo unflatten``
--------------------

::

    pyrepo [<global-options>] unflatten

Convert a "flat module" project (one where all the code is in a
``src/foobar.py`` file) to a "package" project (one where all the code is in a
``src/foobar/`` directory containing an ``__init__.py`` file).  The old flat
module becomes the ``__init__.py`` file of the new package directory, and the
project's ``setup.cfg`` is updated for the change in configuration.


Restrictions
============
``jwodder-pyrepo`` relies on various assumptions about project layout and
formatting; see `the project wiki on GitHub`__ for details.  Most notably, it
does not support the following types of projects:

__ https://github.com/jwodder/pyrepo/wiki/Project-Layout-Specification

- projects that do not use setuptools
- projects that do not use a ``src/`` layout
- projects that do not declare all of their project metadata in ``setup.cfg``
- projects that neither store their version in a ``__version__`` variable in
  the initfile nor use versioningit_
- projects that are not pure Python
- projects containing more than one root-level module/package
- namespace packages
- (``pyrepo init``) projects that support Python 2
- (``pyrepo release``) projects that only support Python 2

.. _versioningit: https://github.com/jwodder/versioningit
