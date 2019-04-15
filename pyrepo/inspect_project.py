from pathlib import Path

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
