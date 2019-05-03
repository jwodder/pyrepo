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

- `pyrepo mkgithub`:
    - If `--repo-name` is not specified, read it from the project's `url`
    - Update the project's `url` et alii if necessary
    - Also set GitHub topics based on project keywords?
    - Push all branches, not just master?
    - Add an option for the Python executable to use to run `setup.py`

- Add subcommands for incrementally adding features (tests, docs, Travis, etc.)
  to an already-templated repository
    - `add-tests`: Create `tox.ini`
    - `add-travis`: Do `add-tests`, create `.travis.yml`, add the appropriate
      badges to the README
    - `add-docs`: Create `docs/*`, add block to `tox.ini`, add documentation
      links to the README, `project_urls`, and main source file docstring
- Add a subcommand for updating the README for `has_pypi` being true
    - When generating a README with `has_pypi = False`, use the GitHub URL in
      the installation instructions, with this command replacing that with the
      project name?
    - Automatically run this command on first release?
- Add a subcommand that regenerates/outputs specified templated files
    - The script should take command line options for overriding the various
      Jinja env vars
- Add a subcommand for updating GitHub description & tags based on the
  project's short description and keywords?

- Templates:
    - Adjust the templates to always include package data, even if there is
      none?
    - When a package has a command, include "Run ``{{command}} --help``" in the
      "see also" paragraph in the module docstring
    - `README.rst.j2`: Use the "Active" repostatus badge when a release has
      already been made for the project
    - `setup.cfg.j2`: Set the "Development Status" classifier to "4 - Beta"
      when a release has already been made for the project

- Write tests
- Move `pyrepo/templates/variables.md` somewhere else
- Rename `inspect_project.py` to something shorter
- Fill in `--help` strings and command docstrings
- Make `twine` a dependency?

- Prior art to investigate and compare against:
    - https://pypi.python.org/pypi/octopusapi
    - https://github.com/audreyr/cookiecutter
    - https://github.com/audreyr/cookiecutter-pypackage
    - https://github.com/pypa/sampleproject
    - https://github.com/jaraco/skeleton
    - https://github.com/ionelmc/cookiecutter-pylibrary

- Write scripts for adding new repositories to Read the Docs, Travis, and
  Codecov.io via their APIs
    - Read the Docs: not possible
        - Write a module with `mechanicalsoup` to do this?
    - Travis: <https://developer.travis-ci.org/resource/repository#activate>?
        - Is this step unnecessary on travis-ci.com?
    - Codecov.io: done automatically when test results are submitted
- Add templates for:
    - `CHANGELOG.md`?
    - `CONTRIBUTORS.md`

- Write a "RATIONALE.md" (or "BIKESHED.md"?) file for reminding me why I did
  certain things / why #2EFFFC is the correct color to paint a bikeshed
    - cf. <https://blog.ionelmc.ro/2014/05/25/python-packaging/>
- Standardize Read the Docs settings
- Standardize Travis settings?
