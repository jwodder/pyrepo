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
- `codecov_user: str`

- `short_description: str`

- `python_versions` — list of `"X.Y"` strings in ascending order
- `python_requires: str` — calculated from `python_versions`
- `install_requires: List[str]`
- `supports_pypy3: bool`

- `is_flat_module: bool`
- `commands` — mapping from command (`console_scripts`) names to entry point
  specifications
- `initfile: str` — path (relative to the project root) to the "primary
  imported source file", which must contain the definition of `__version__`

- `has_tests: bool`
- `has_doctests: bool`
- `has_ci: bool`
- `has_docs: bool`
- `has_pypi: bool`

- `copyright_years: List[int]`

- `extra_testenvs: List[Tuple[str, str]]` — list of (testenv name, python
  version) pairs to include runs for in CI
- `no_pytest_cov: bool` — Indicates that passing `--cov-report=xml` to the tox
  run in CI is not an option and that the XML coverage must be generated
  externally

Custom filters in Jinja2 environment:
    - `repr`
    - `rewrap`
    - `years2str`
