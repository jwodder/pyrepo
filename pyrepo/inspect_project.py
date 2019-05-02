import ast
from   configparser      import ConfigParser
import time
from   pathlib           import Path
import re
from   pkg_resources     import yield_lines
from   setuptools.config import read_configuration
from   .                 import util  # Import module to keep mocking easy

def inspect_project(dirpath):
    if not (dirpath / 'setup.py').exists():
        raise ValueError('No setup.py in project root')
    if not (dirpath / 'setup.cfg').exists():
        raise ValueError('No setup.cfg in project root')
    cfg = read_configuration(str(dirpath / 'setup.cfg'))
    env = {
        "project_name": cfg["metadata"]["name"],
        "short_description": cfg["metadata"]["description"],
        "author": cfg["metadata"]["author"],
        "author_email": cfg["metadata"]["author_email"],
        "python_requires": cfg["options"]["python_requires"],
        "install_requires": cfg["options"].get("install_requires", []),
        "importable": "version" in cfg["metadata"],
    }

    if cfg["options"].get("packages"):
        env["is_flat_module"] = False
        env["import_name"] = cfg["options"]["packages"][0]
    else:
        env["is_flat_module"] = True
        env["import_name"] = cfg["options"]["py_modules"][0]

    env["python_versions"] = []
    for clsfr in cfg["metadata"]["classifiers"]:
        m = re.fullmatch(r'Programming Language :: Python :: (\d+\.\d+)', clsfr)
        if m:
            env["python_versions"].append(m.group(1))

    env["commands"] = {}
    try:
        commands = cfg["options"]["entry_points"]["console_scripts"]
    except KeyError:
        pass
    else:
        for cmd in commands:
            k, v = re.split(r'\s*=\s*', cmd, maxsplit=1)
            env["commands"][k] = v

    m = re.fullmatch(
        r'https://github.com/([^/]+)/([^/]+)',
        cfg["metadata"]["url"],
    )
    assert m, 'Project URL is not a GitHub URL'
    env["github_user"] = m.group(1)
    env["repo_name"] = m.group(2)

    if "Documentation" in cfg["metadata"]["project_urls"]:
        m = re.fullmatch(
            r'https?://([-a-zA-Z0-9]+)\.(?:readthedocs|rtfd)\.io',
            cfg["metadata"]["project_urls"]["Documentation"],
        )
        assert m, 'Documentation URL is not a Read the Docs URL'
        env["rtfd_name"] = m.group(1)
    else:
        env["rtfd_name"] = env["project_name"]

    if "Say Thanks!" in cfg["metadata"]["project_urls"]:
        m = re.fullmatch(
            r'https://saythanks\.io/to/([^/]+)',
            cfg["metadata"]["project_urls"]["Say Thanks!"],
        )
        assert m, 'Invalid Say Thanks! URL'
        env["saythanks_to"] = m.group(1)
    else:
        env["saythanks_to"] = None

    if (dirpath / 'tox.ini').exists():
        toxcfg = ConfigParser(interpolation=None)
        toxcfg.read(str(dirpath / 'tox.ini'))
        env["has_tests"] = toxcfg.has_section("testenv")

    env["has_travis"] = (dirpath / '.travis.yml').exists()
    env["has_docs"] = (dirpath / 'docs' / 'index.rst').exists()

    env["travis_user"] = NotImplemented
    env["codecov_user"] = NotImplemented
    env["has_pypi"] = NotImplemented
    env["copyright_years"] = NotImplemented

    return env

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
        if name.isidentifier() and name != 'setup':
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

def parse_requirements(filepath):
    variables = {
        "__python_requires__": None,
        "__requires__": None,
    }
    try:
        with open(filepath, encoding='utf-8') as fp:
            for line in fp:
                m = re.fullmatch(
                    r'\s*#\s*python\s*((?:[=<>!~]=|[<>]|===)\s*\S(?:.*\S)?)\s*',
                    line,
                    flags=re.I,
                )
                if m:
                    variables["__python_requires__"] = m.group(1)
                    break
            fp.seek(0)
            variables["__requires__"] = list(yield_lines(fp))
    except FileNotFoundError:
        pass
    return variables
