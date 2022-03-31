In Development
--------------
- Give `pyrepo release` a `--date` flag
- Support projects that use versioningit
    - Add a `uses_versioningit: bool` template variable
- Update for setuptools 61.0.0
- Templates:
    - Update `sphinx-copybutton` version to `~=0.5.0`
    - Update `.readthedocs.yml` to use a `build:` section and rename the file
      to `.readthedocs.yaml`
    - Update `.pre-commit-config.yaml`
- Internal API:
    - Store project details in a `ProjectDetails` class
    - Add `Templater` and `TemplateWriter` classes

v2022.2.6
---------
Start tagging at notable points
