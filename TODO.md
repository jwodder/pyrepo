- Write a script that takes a package name (and other metadata) and generates
  the various project files for it in the current directory
    - Include scripts for incrementally adding features (tests, docs, doctests,
      Travis, etc.) to an already-templated repository
    - Include a script that regenerates/outputs specified templated files
        - The script should take command line options for overriding the
          various Jinja env vars
    - Prior art to investigate and compare against:
        - https://pypi.python.org/pypi/octopusapi
        - https://github.com/dghubble/pypkg
        - https://github.com/audreyr/cookiecutter
        - https://github.com/audreyr/cookiecutter-pypackage
        - https://github.com/pypa/sampleproject
        - https://github.com/jaraco/skeleton
        - https://github.com/ionelmc/cookiecutter-pylibrary

- Write scripts for adding new repositories to Read the Docs, Travis, and
  Codecov.io via their APIs
    - Read the Docs: not possible
    - Travis: <https://developer.travis-ci.org/resource/repository#activate>
    - Codecov.io: done automatically when test results are submitted
- Add templates for:
    - `docs/index.rst` (and other `docs/*.rst` files?)
    - `CHANGELOG.md`
    - `CONTRIBUTORS.md`
- Improve `pyrelease.py`
    - Replace with a customized <https://pypi.python.org/pypi/zest.releaser>?

- Write a "RATIONALE.md" (or "BIKESHED.md"?) file for reminding me why I did
  certain things / why #2EFFFC is the correct color to paint a bikeshed
    - cf. <https://blog.ionelmc.ro/2014/05/25/python-packaging/>
- Standardize Read the Docs settings
- Standardize Travis settings?
