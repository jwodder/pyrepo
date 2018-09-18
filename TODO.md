- Write a script that takes a package name (and other metadata) and generates
  the various project files for it in the current directory
    - Include scripts for incrementally adding features (tests, docs, doctests,
      Travis, etc.) to an already-templated repository
    - Prior art to investigate and compare against:
        - https://pypi.python.org/pypi/octopusapi
        - https://github.com/dghubble/pypkg
        - https://github.com/audreyr/cookiecutter
        - https://github.com/audreyr/cookiecutter-pypackage
        - https://github.com/pypa/sampleproject
        - https://github.com/jaraco/skeleton
        - https://github.com/ionelmc/cookiecutter-pylibrary
    - When creating `setup.py`/`setup.cfg`, if a `requirements.txt` file
      already exists in the project directory, use its contents for
      `install_requires`
    - Determine the year used in the LICENSE and `docs/conf.py` copyright by
      taking the year of every Git commit in the project
        - `git log --format=%ad --date=format:%Y`
    - Properly word-wrap the installation instructions in `README.rst` (and the
      "see also" message in the `__init__.py` docstring?) when templating

- Write scripts for adding new repositories to Read the Docs, Travis, and
  Codecov.io via their APIs
    - Readthedocs: not possible
    - Travis: <https://developer.travis-ci.org/resource/repository#activate>
    - Codecov.io: done automatically when test results are submitted
- Add templates for:
    - `docs/index.rst` (and other `docs/*.rst` files?)
    - `CHANGELOG.md`
    - `CONTRIBUTORS.md`
    - `test/test_FEATURE.py`?
- Improve `pyrelease.py`
    - Replace with a customized <https://pypi.python.org/pypi/zest.releaser>?
    - Make the pre-release steps also update the year range in `LICENSE` and
      `docs/conf.py`?

- Write a "RATIONALE.md" (or "BIKESHED.md"?) file for reminding me why I did
  certain things / why #2EFFFC is the correct color to paint a bikeshed
    - cf. <https://blog.ionelmc.ro/2014/05/25/python-packaging/>
- Standardize Readthedocs settings
- Standardize Travis settings?
