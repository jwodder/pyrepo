In Development
--------------
- `pyrepo release` will now error if the project uses versioningit and no
  explicit version or bump option is given on the command line
- Use `tomllib` on Python 3.11
- Remove support for PGP-signing PyPI uploads
- Disable coloring of log messages when stderr is redirected
- `pyrepo mkgithub` now sets `delete_branch_on_merge` to `true` in
  newly-created repositories
- Update build dependency to 1.0
- `pyrepo init`: Generate a `.github/dependabot.yml` file when `--ci` is set
- `pyrepo mkgithub`: Create custom labels used by `.github/dependabot.yml`
  template
- `pyrepo mkgithub`: Properly sanitize keywords used as topics
- Templates:
    - Add 'A' to enabled flake8 checks in `tox.ini`
    - Update coverage paths config in `tox.ini` for Coverage v7
    - Update `.pre-commit-config.yaml`
    - Annotate `copyright` line in `docs/conf.py` with `noqa: A001`
    - `test.yml`: Update `actions/checkout` to `v4`
    - `test.yml`: Don't run on pushes to dependabot PR branches
    - `test.yml`: Cancel concurrent jobs

v2022.10.16
-----------
- Drop support for the `[pyversions]` config section
- Option defaults given in the `[options]` config section are no longer copied
  to command subsections
- Change the config file format to TOML
    - Config keys are no longer case-insensitive
- `pyrepo init`:
    - The `--project-name`, `--repo-name`, and `--rtfd-name` options may now be
      set to Jinja2 templates using the variables `project_name` (except
      `--project-name` itself) and `import_name`, and `--author-email`
      templates may now use the variable `import_name`.
    - The default version comparison operator used in `python_requires` fields
      in `setup.cfg` has been changed from `~=` to `>=`.
- Stop including "Development Status" classifiers in `setup.cfg`, and no longer
  make `pyrepo release` manage them
- Add a `pyrepo drop-pyversion` command and `Project.drop_pyversion()` method
  for removing support for the lowest minor Python version
- `pyrepo begin-dev` now does nothing if the project is already in "dev mode"
- Templates:
    - The presence of `pypy3` in the envlist in `tox.ini` is now affected by
      `supports_pypy`, and the exact PyPy version(s) used is now based on the
      CPython major versions supported by the latest PyPy series
    - The installation instructions in `README.rst` and `docs/index.rst` have
      been changed from "to install {name} and its dependencies" to "to install
      it"
    - `pyproject.toml`: Remove `wheel` from `build-system.requires`
    - `test.yml`: Update action versions
    - `tox.ini`: Remove version specifiers from deps
    - `.readthedocs.yaml`: Update `.build.os` to `ubuntu-22.04`
- Internal API:
    - Make `configure()` store option defaults in `ctx.default_map`
    - Rename `supports_pypy3` to `supports_pypy`
    - Replace pydantic with dataclasses + cattrs

v2022.6.20
----------
- Give `pyrepo release` a `--date` flag
- Give `pyrepo begin-dev` a `--no-next-version` flag
- `pyrepo release`: Don't upload projects with "Private" classifiers to PyPI
- Support projects that use versioningit
    - Add a `uses_versioningit: bool` template variable
- Support CHANGELOG headers of the form `vDATEVERSION`
- Update for setuptools 61.0.0
- Update twine dependency to 4.0
- Templates:
    - Update `sphinx-copybutton` version to `~=0.5.0`
    - Update `.readthedocs.yml` to use a `build:` section and rename the file
      to `.readthedocs.yaml`
    - Update `.pre-commit-config.yaml`
    - Update `Sphinx` version to `~=5.0`
    - `setup.cfg`: Use `find_namespace:` instead of `find:` (See
      <https://github.com/pypa/setuptools/issues/3340>)
- Internal API:
    - Store project details in a `ProjectDetails` class
    - Add `Templater` and `TemplateWriter` classes
    - Include classifiers in project details

v2022.2.6
---------
Start tagging at notable points
