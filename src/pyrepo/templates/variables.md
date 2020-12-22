- `name: str` — the name of the project as it is/will be known on PyPI
- `import_name: str`
- `repo_name: str`
- `rtfd_name: str`
- `author: str`
- `author_email: str`
- `version: str`
- `keywords: List[str]`

- `github_user: str`
- `codecov_user: str`

- `short_description: str`

- `python_versions` — list of `"X.Y"` strings in ascending order
- `python_requires: str` — calculated from `python_versions`
- `install_requires: List[str]`
- `supports_pypy3: bool`

- `is_flat_module: bool`
- `commands` — mapping from command (`console_scripts`) names to entry point
  specifications

- `has_tests: bool`
- `has_typing: bool`
- `has_doctests: bool`
- `has_ci: bool`
- `has_docs: bool`
- `has_pypi: bool`

- `copyright_years: List[int]`

- `extra_testenvs: Dict[str, str]` — extra testenvs to include runs for in CI,
  as a mapping from testenv name to Python version

Custom filters in Jinja2 environment:
    - `repr`
    - `rewrap`
    - `years2str`
