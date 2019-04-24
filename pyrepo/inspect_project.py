import ast
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

def find_module(dirpath: Path):
    results = []
    for flat in dirpath.glob('*.py'):
        name = flat.stem
        if name.isidentifier():
            results.append({
                "import_name": name,
                "is_flat_module": True,
            })
    for pkg in dirpath.glob('*/__init__.py'):
        name = pkg.parent.name
        if name.isidentifier():
            results.append({
                "import_name": name,
                "is_flat_module": False,
            })
    if len(results) > 1:
        raise ValueError('Multiple Python modules in repository')
    elif not results:
        raise ValueError('No Python modules in repository')
    else:
        return results[0]

def extract_requires(filename):
    ### TODO: Split off the destructive functionality so that this can be run
    ### idempotently/in a read-only manner
    variables = {
        "__python_requires__": None,
        "__requires__": None,
    }
    with open(filename, 'rb') as fp:
        src = fp.read()
    lines = src.splitlines(keepends=True)
    dellines = []
    tree = ast.parse(src)
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.Assign) \
                and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in variables:
            variables[node.targets[0].id] = ast.literal_eval(node.value)
            if i+1 < len(tree.body):
                dellines.append(slice(node.lineno-1, tree.body[i+1].lineno-1))
            else:
                dellines.append(slice(node.lineno-1))
    for sl in reversed(dellines):
        del lines[sl]
    with open(filename, 'wb') as fp:
        fp.writelines(lines)
    return variables
