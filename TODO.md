- Write a script that takes a package name (and other metadata) and generates
  the various project files for it in the current directory
    - Include scripts for incrementally adding features (tests, docs, doctests,
      Travis, etc.) to an already-templated repository
- Write scripts for adding new repositories to Read the Docs, Travis, and
  Coveralls via their APIs
    - Readthedocs: not possible
    - Travis: <https://developer.travis-ci.org/resource/repository#activate>
    - Coveralls: not possible?
- Add template for `docs/index.rst` (and other `docs/*.rst` files?)
- `tox.ini`: `docs`: Can `rm -rf _build` be forgone in favor of adding `-a -E`
  to the `sphinx-build` command?
- Determine the year used in the LICENSE and `docs/conf.py` copyright by taking
  the year of every Git commit in the project
- When creating `setup.py`/`setup.cfg`, if a `requirements.txt` file already
  exists in the project directory, use its contents for `install_requires`
- Add an option for enabling doctests in `tox.ini`?
- Properly word-wrap the installation instructions in `README.rst` (and the
  "see also" message in the `__init__.py` docstring?) when templating
- Add a CHANGELOG template
- Incorporate `pyrelease.sh`
