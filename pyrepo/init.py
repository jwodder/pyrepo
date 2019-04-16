#!/usr/bin/python3
from   pathlib          import Path
import re
import time
import click
from   in_place         import InPlace
from   jinja2           import Environment, PackageLoader
from   pkg_resources    import yield_lines
from   .                import util  # Import module to keep mocking easy
from   .inspect_project import is_flat

AUTHOR = 'John Thorvald Wodder II'
EMAIL_HOSTNAME = 'varonathe.org'

MIN_PY3_SUBVER = 4
MAX_PY3_SUBVER = 7

def pyver_range(min_subver):
    return list(map('3.{}'.format, range(min_subver, MAX_PY3_SUBVER+1)))

@click.command()
@click.option('--author', default=AUTHOR)
@click.option('--author-email')
@click.option('-c', '--command')
@click.option('-d', '--description', prompt=True)
@click.option('--docs/--no-docs', default=False)
@click.option('--import-name')
@click.option('--importable/--no-importable', default=None)
@click.option(
    '-P', '--min-pyver',
    type=click.Choice(pyver_range(MIN_PY3_SUBVER)),
    default=f'3.{MIN_PY3_SUBVER}',
)
@click.option('--repo-name')
@click.option('--rtfd-name')
@click.option('--tests/--no-tests', default=False)
@click.argument('project_name')
def init(project_name, min_pyver, import_name, repo_name, author, author_email,
         description, tests, docs, rtfd_name, importable, command):
    if import_name is None:
        import_name = project_name.replace('-', '_').replace('.', '_')
    if repo_name is None:
        ### TODO: If the repository has a GitHub remote, use that to set
        ### `repo_name`
        repo_name = project_name
    if rtfd_name is None:
        rtfd_name = project_name
    if author_email is None:
        author_email = project_name.replace('_', '-') + '@' + EMAIL_HOSTNAME

    is_flat_module = is_flat(Path(), import_name)

    try:
        with open('requirements.txt') as fp:
            install_requires = list(yield_lines(fp))
    except FileNotFoundError:
        ### TODO: Check source file for __requires__ attribute (and then remove
        ### it)
        install_requires = []

    ### TODO: Support setting the entry point function name to something other
    ### than "main" on the command line
    ### TODO: Autodetect `if __name__ == '__main__':` lines in import_name.py /
    ### import_name/__main__.py and set `commands` accordingly
    if command is None:
        commands = {}
    elif is_flat_module:
        commands = {command: f'{import_name}:main'}
    else:
        commands = {command: f'{import_name}.__main__:main'}

    if importable is None:
        if not install_requires:
            importable = True
        elif (Path(import_name) / '__main__.py').exists():
            importable = True
        else:
            importable = False

    env = {
        "project_name": project_name,
        "import_name": import_name,
        "repo_name": repo_name,
        "rtfd_name": rtfd_name,
        "author": author,
        "author_email": author_email,
        "short_description": description,
        "python_versions": pyver_range(int(min_pyver.partition('.')[2])),
        "python_requires": "~=" + min_pyver,
        "is_flat_module": is_flat_module,
        "importable": importable,
        "install_requires": install_requires,
        "commands": commands,
        "copyright_years": sorted(set(get_commit_years() + [time.localtime().tm_year])),
        "has_travis": tests,
        "has_docs": docs,
        "has_pypi": False,
        "has_doctests": False,
    }

    init_packaging(env)
    ###if tests:
    ###    init_tests(env)
    ###if docs:
    ###    init_docs(env)

def init_packaging(env):
    if Path('setup.py').exists():
        raise click.UsageError('setup.py already exists')
    for filename in [
        '.gitignore', 'MANIFEST.in', 'README.rst', 'setup.cfg', 'setup.py',
    ]:
        if not Path(filename).exists():
            add_templated_file(filename, env)

    if Path('LICENSE').exists():
        util.ensure_license_years('LICENSE', env["copyright_years"])
        util.runcmd('git', 'add', 'LICENSE')
    else:
        add_templated_file('LICENSE', env)

    if env["is_flat_module"]:
        init_src = Path(env["import_name"] + '.py')
    else:
        init_src = Path(env["import_name"]) / '__init__.py'
    with InPlace(init_src, mode='t') as fp:
        started = False
        for line in fp:
            if line.startswith('#!') \
                or (line.lstrip().startswith('#')
                    and re.search(r'coding[=:]\s*([-\w.]+)', line)):
                pass
            elif not started:
                print(jinja_env().get_template('init.j2').render(env), file=fp)
                print(file=fp)
                started = True
            print(line, file=fp, end='')
    util.runcmd('git', 'add', str(init_src))

    if Path('requirements.txt').exists():
        util.runcmd('git', 'rm', '-f', 'requirements.txt')


###def init_tests(env):
    ### test/, tox.ini, .travis.yml(?)
    ### badges in README

###def init_docs(env):
    ### docs/*, tox.ini block, documentation URL in setup.cfg and README

def add_templated_file(filename, env):
    Path(filename).write_text(
        jinja_env().get_template(filename).render(env).rstrip() + '\n',
        encoding='utf-8',
    )
    util.runcmd('git', 'add', filename)

def get_commit_years():
    return sorted(set(map(
        int,
        util.readcmd('git', 'log', '--format=%ad', '--date=format:%Y')
            .splitlines(),
    )))

_jinja_env = None
def jinja_env():
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=PackageLoader('pyrepo', 'templates'),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        _jinja_env.filters['repr'] = repr
        _jinja_env.filters['years2str'] = util.years2str
    return _jinja_env
