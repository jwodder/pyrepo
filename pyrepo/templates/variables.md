- `project_name: str`
- `import_name: str`
- `repo_name: str`
- `rtfd_name: str`
- `author: str`
- `author_email: str`
- `saythanks_to: str` — username in saythanks.io URL to include in README and
  `project_urls`

- `short_description: str`

- `python_versions` — list of `"X.Y"` strings in ascending order
- `python_requires: str` — calculated from `python_versions`
- `install_requires: list[str]`

- `is_flat_module: bool`
- `importable: bool` — whether importing the package from within `setup.py` is
  an option
- `commands` — mapping from command (`console_scripts`) names to entry point
  specifications

- `has_travis: bool`
- `has_docs: bool`
- `has_pypi: bool`
- `has_doctests: bool`

- `copyright_years: list[int]`

Custom filters in Jinja2 environment:
    - `repr`
    - `years2str`
