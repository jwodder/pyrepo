- Write tests
- Fill in `--help` strings and command docstrings
- Autodetect project root by looking for `.git` folder, thereby allowing
  commands to be run from deeper in a project
    - Doable with `git rev-parse --show-toplevel`
- Move `pyrepo/templates/variables.md` somewhere else
- Support namespace packages?
- Make this a package in the `jwodder` namespace?
- Make the new variables added in e7039fc available during `pyrepo init`
    - Have `keywords` set to `[]`

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
    - Add a `--pypi/--no-pypi` option for controlling the `has_pypi` variable
    - Better handle projects whose `python_requires` includes EOL versions
        - Currently, pyrepo ignores the EOL versions when generating the list
          of versions to use in the classifiers, `tox.ini`, and `.travis.yml,
          but the `python_requires` string that includes the old versions is
          still used unmodified
    - Support initializing a project with a `src` layout

- `pyrepo release`:
    - Add an option for setting the new version number from the command line
    - Support configuring the following via the config file:
        - whether to sign the version tag
        - whether to sign assets
        - program to use for signing
        - where & whether to upload on Dropbox
        - whether to create a GitHub release
        - whether to upload to GitHub
        - GitHub API credentials?
        - whether to run tox
        - whether to start a shell to examine the assets after building but
          before uploading?
        - Python executable to use to run `setup.py`?
    - Move the signing of the build assets to after committing & tagging?
    - Also update & manage `docs/changelog.rst` when `docs/` exists

- `pyrepo mkgithub`:
    - Update the project's `url` et alii if necessary
    - Also set GitHub topics based on project keywords?
    - Push all branches, not just master?
    - Push all tags
    - Support creating the repository in an organization?

- `pyrepo template`:
    - Add command line options for overriding the various Jinja env vars
    - Preserve keywords and classifiers when retemplating `setup.cfg`?

- Add subcommands for incrementally adding features (tests, docs, Travis, etc.)
  to an already-templated repository
    - `add-tests`: Create `tox.ini`
    - `add-travis`: Do `add-tests`, create `.travis.yml`, add the appropriate
      badges to the README
    - `add-docs`: Create `docs/*`, add block to `tox.ini`, add documentation
      links to the README, `project_urls`, and main source file docstring
        - The initial content of `docs/index.rst` should be taken from the
          README
        - Should the adding of documentation links be split into a separate
          command?
- Add a subcommand for updating the README for `has_pypi` being true
    - When generating a README with `has_pypi = False`, use the GitHub URL in
      the installation instructions, with this command replacing that with the
      project name?
    - Automatically run this command on first release?
- Add a subcommand for updating GitHub description & tags based on the
  project's short description and keywords?
- Add a subcommand for converting a flat module to a non-flat package?
- Add a subcommand for converting to a `src` layout?

- Templates:
    - Adjust the templates to always include package data, even if there is
      none?
    - When a package has a command, include "Run ``{{command}} --help``" in the
      "see also" paragraph in the module docstring
    - Is `codecov_user` ever not the same as `github_user`?  What about
      `travis_user`?
    - Add `has_release` (equivalent to `has_pypi`?) and `is_stable` variables
      (the latter defined by the version number being at least 1.0) that are
      used to select the repostatus badge in the README and the development
      status trove classifier
    - When `has_pypi` is false, the installation instructions in the README
      should refer to the GitHub URL, not the project name
    - Add templates for:
        - `CHANGELOG.md`?
        - `CONTRIBUTORS.md`
    - Switch to travis-ci.com?
    - Set the pytest etc. version in `tox.ini` based on the smallest Python
      version supported by the project?
    - Support `src` layouts (e.g., in the arguments to `pytest` in `tox.ini`)
    - Add a `pyproject.toml` template?

- Prior art to investigate and compare against:
    - https://pypi.python.org/pypi/octopusapi
    - https://github.com/audreyr/cookiecutter
    - https://github.com/audreyr/cookiecutter-pypackage
    - https://github.com/pypa/sampleproject
    - https://github.com/jaraco/skeleton
    - https://github.com/ionelmc/cookiecutter-pylibrary

- Write scripts for adding new repositories to Read the Docs, Travis, and
  Codecov.io via their APIs
    - Read the Docs: not possible?
        - Double-check <https://docs.readthedocs.io/en/stable/api/v3.html>
        - Write a module with `mechanicalsoup` to do this?
    - Travis: automatic as of the move to travis-ci.com?
    - Codecov.io: done automatically when test results are submitted
