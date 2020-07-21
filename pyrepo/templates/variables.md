- `project_name: str`
- `import_name: str`
- `repo_name: str`
- `rtfd_name: str`
- `author: str`
- `author_email: str`
- `saythanks_to: str` — username in saythanks.io URL to include in README and
  `project_urls`
- `version: str`
- `keywords: List[str]`

- `github_user: str`
- `travis_user: str`
- `codecov_user: str`

- `short_description: str`

- `python_versions` — list of `"X.Y"` strings in ascending order
- `python_requires: str` — calculated from `python_versions`
- `install_requires: List[str]`

- `is_flat_module: bool`
- `commands` — mapping from command (`console_scripts`) names to entry point
  specifications
- `src_layout: bool`
- `pep517: bool` — whether the project has a `pyproject.toml` file
- `initfile: str` — path (relative to the project root) to the "primary
  imported source file", which must contain the definition of `__version__`

- `has_tests: bool`
- `has_doctests: bool`
- `has_travis: bool`
- `has_docs: bool`
- `has_pypi: bool`

- `copyright_years: List[int]`

Custom filters in Jinja2 environment:
    - `repr`
    - `rewrap`
    - `years2str`
