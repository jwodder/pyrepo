- `project_name: str`
- `import_name: str`
- `repo_name: str`
- `rtfd_name: str`
- `email_username: str` — the part before the '@' in the author e-mail

- `short_description: str`

- `python_versions` — list of `"X.Y"` strings in ascending order
- `py2_versions`
- `py3_versions`
- `py2 = '2.7' in python_versions` — whether any Python 2 versions (and thus
  also PyPy) are supported (It's assumed Python 3 is always supported)
- `python_requires: str` — calculated from `python_versions`

- `is_flat_module: bool`
- `importable: bool` — whether importing the package from within `setup.py` is
  an option

- `has_travis`
- `has_docs`
- `has_pypi`
- `has_doctests`

- `copyright_year: str`

Constants:
    - `author = 'John Thorvald Wodder II'`
    - `email_hostname = 'varonathe.org'`

To include in Jinja2 environment:
    - `repr`
