- Write more tests
- Support namespace packages?
- Make this a package in the `jwodder` namespace?
- Rename the actual Python import package to `jwodder_pyrepo`?
- Make `configure()` store the config file values in `ctx.default_map`
    - Use Click 8's new features to handle the precedence order of `pyrepo init
      --python-requires`
    - Simplify the option handling in `pyrepo release` to take advantage of
      this
- Change `__python_requires__` to `__requires_python__` to match PEP 621?
    - Accept both forms as synonyms?
- Rename `supports_pypy3` to `supports_pypy` and determine what versions of
  PyPy to support based on the supported Python versions
- Make `inspect_project()` and `init` log at DEBUG level
- Require default `init` config values to be in `[options.init]` in the config
  file instead of under just `[options]`?  I.e., don't copy values from
  `[options]` to other sections?
- Is `codecov_user` ever not the same as `github_user`?
- Support reading project-specific configuration from `pyproject.toml` and/or
  some dotfile?
- Figure out how to rewrite the dynamic module loading in `__main__.py` using
  `pkgutil.iter_modules()`
- Instead of filling up `test/data` with folders full of test cases, write a
  function for generating a complete sample project from a set of parameters
  (The function will still need folders full of test cases, though)

- Support projects supporting multiple major versions of Python
    - Make `Project.add_pyversion()` add a "Programming Language :: Python ::
      X" classifier when adding the first minor version of a major version.
    - Make `Project.add_pyversion()` remove a "Programming Language :: Python
      :: X :: Only" classifier when it no longer applies
    - Support versions with different major versions in the config file's
      "[pyversions]"

- `pyrepo init`:
    - Support `project_name`, `repo_name`, and `rtfd_name` as Jinja2 templates
      with access to `import_name` and (except for `project_name` itself)
      `project_name`
    - If the repository already has a GitHub remote, use that to set the
      default `repo_name` (and `github_user`?)
    - `--command`: Support setting the entry point function name to something
      other than "main" on the command line
    - Autodetect `if __name__ == '__main__':` lines in `import_name.py` /
      `import_name/__main__.py` and set `commands` accordingly
    - Add a `--pypi/--no-pypi` option for controlling the `has_pypi` variable?
    - Better handle projects whose `python_requires` includes EOL versions
        - Currently, pyrepo ignores the EOL versions when generating the list
          of versions to use in the classifiers, `tox.ini`, and `test.yml,
          but the `python_requires` string that includes the old versions is
          still used unmodified
    - Add an option for setting the starting version
    - Split off all of the variable-determining code into a (nondestructive)
      `inspect_new_project()` function
    - Should `has_doctests` be autodetected the same way as for an initialized
      project?

- `pyrepo release`:
    - Support configuring the following via the config file and command line:
        - whether to sign the version tag
        - whether to create a GitHub release
        - whether to upload to GitHub
        - whether to start a shell to examine the assets after building but
          before uploading?
    - Move the signing of the build assets to after committing & tagging?
    - Get the program to use for signing from git's `gpg.program` config value

- `pyrepo mkgithub`:
    - Update the project's `url` et alii if necessary
    - Push all branches, not just master?
    - Push all tags
    - Support creating the repository in an organization?

- `pyrepo template`:
    - Add command line options for overriding the various Jinja env vars
    - Preserve classifiers etc. when retemplating `setup.cfg`?

- `pyrepo make`:
    - Support setting options via the config file

- Add subcommands for incrementally adding features (tests, docs, CI, etc.) to
  an already-templated repository
    - `add-tests`: Create `tox.ini`
        - Include a `--doctests/--no-doctests` option
    - `add-doctests`
        - Also add `rm-doctests`
    - `add-ci`: Do `add-tests`, create `test.yml`, add the appropriate badges
      to the README
    - `add-docs`: Create `docs/*` and `.readthedocs.yml`, add block to
      `tox.ini`, add documentation links to the README, `project_urls`, and
      main source file docstring
        - The initial content of `docs/index.rst` should be taken from the
          README
        - Should the adding of documentation links be split into a separate
          command?
- Add a subcommand for updating the README for `has_pypi` being true
    - When generating a README with `has_pypi = False`, use the GitHub URL in
      the installation instructions, with this command replacing that with the
      project name?
    - Automatically run this command on first release
- Add a subcommand for updating GitHub description & tags based on the
  project's short description and keywords?
- Add subcommands for adding & removing a Python version from the set of
  supported versions

- Templates:
    - When a package has a command, include "Run ``{{command}} --help``" in the
      "see also" paragraph in the module docstring?
    - Add `has_release` (equivalent to `has_pypi`?) and `is_stable` variables
      (the latter defined by the version number being at least 1.0) that are
      used to select the repostatus badge in the README and the development
      status trove classifier
    - When `has_pypi` is false, the installation instructions in the README
      should refer to the GitHub URL, not the project name
    - Add template for `CONTRIBUTORS.md`?
    - Support having the same extra testenv run against multiple Python
      versions
    - Make `supports_pypy3` affect the envlist in `tox.ini`

- Write a command for adding new repositories to Read the Docs
    - Not possible?  Double-check
      <https://docs.readthedocs.io/en/stable/api/v3.html>
    - Write a module with `mechanicalsoup` to do this?
