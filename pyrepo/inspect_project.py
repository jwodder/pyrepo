import time
from   pathlib import Path
from   .       import util  # Import module to keep mocking easy

def is_flat(dirpath, import_name):
    flat_src = Path(dirpath, import_name + '.py')
    pkg_init_src = Path(dirpath, import_name) / '__init__.py'
    if flat_src.exists() and pkg_init_src.exists():
        raise ValueError(f'Both {import_name}.py and {import_name}/__init__.py'
                         f' present in repository')
    elif flat_src.exists():
        return True
    elif pkg_init_src.exists():
        return False
    else:
        raise ValueError(f'Neither {import_name}.py nor'
                         f' {import_name}/__init__.py present in repository')

def get_commit_years(dirpath, include_now=True):
    years = set(map(
        int,
        util.readcmd(
            'git', '-C', str(dirpath), 'log', '--format=%ad', '--date=format:%Y'
        ).splitlines(),
    ))
    if include_now:
        years.add(time.localtime().tm_year)
    return sorted(years)
