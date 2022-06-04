In Development
--------------
- Give `pyrepo release` a `--date` flag
- Support projects that use versioningit
    - Add a `uses_versioningit: bool` template variable
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

v2022.2.6
---------
Start tagging at notable points
