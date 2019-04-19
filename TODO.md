- Write a script that takes a package name (and other metadata) and generates
  the various project files for it in the current directory
    - Include subcommands for incrementally adding features (tests, docs,
      doctests, Travis, etc.) to an already-templated repository
        - The docs command should also add documentation links to the README
          and `project_urls`
        - The Travis command should also add the appropriate badges to the
          README
        - Add a command for updating the README for `has_pypi` being true
            - When generating a README with `has_pypi = False`, use the GitHub
              URL in the installation instructions, with this command replacing
              that with the project name?
            - Automatically run this command on first release?
    - Include a subcommand that regenerates/outputs specified templated files
        - The script should take command line options for overriding the
          various Jinja env vars
    - Convert `mypyrepo.sh` to a subcommand
    - Add a subcommand for updating GitHub description & tags based on the
      project's short description and keywords?
    - Add support for a config file for configuring:
        - `author`
        - `author_email` (as a Jinja2 template)
        - saythanks.io URL (including unsetting)
        - min & max Python 3 subversions
        - Releasing:
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
    - If `--min-pyver` is not given on the command line, try to determine it by
      looking in the Python source for a `__python_requires__` assignment and
      by looking in `requirements.txt` for a `# Python ~= 3.X` comment
        - Handle both `>= 3.X` and `~= 3.X` requirements
- Adjust the templates to always include package data, even if there is none?
- Write tests
- Move `pyrepo/templates/variables.md` somewhere else
- When a package has a command, include "Run ``{{command}} --help``" in the
  "see also" paragraph in the module docstring
- Give `release` an option for setting the version number from the command line
- Rename `inspect_project.py` to something shorter
- Fill in `--help` strings and command docstrings

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
    - Codecov.io: done automatically when test results are submitted
- Add templates for:
    - `docs/index.rst` (and other `docs/*.rst` files?)
    - `CHANGELOG.md`
    - `CONTRIBUTORS.md`

- Write a "RATIONALE.md" (or "BIKESHED.md"?) file for reminding me why I did
  certain things / why #2EFFFC is the correct color to paint a bikeshed
    - cf. <https://blog.ionelmc.ro/2014/05/25/python-packaging/>
- Standardize Read the Docs settings
- Standardize Travis settings?
