#!/usr/bin/python3
from   pathlib              import Path
import re
import click
from   in_place             import InPlace
from   jinja2               import Environment, PackageLoader
from   packaging.specifiers import SpecifierSet
from   pkg_resources        import yield_lines
from   .                    import inspect_project, util

@click.command()
@click.option('--author')
@click.option('--author-email')
@click.option('-c', '--command')
@click.option('-d', '--description', prompt=True)
@click.option('--docs/--no-docs', default=False)
@click.option('-i', '--import-name')
@click.option('--importable/--no-importable', default=None)
@click.option('-p', '--project-name')
@click.option('-P', '--python-requires')
@click.option('--repo-name')
@click.option('--rtfd-name')
@click.option('--saythanks-to', metavar='USER')
@click.option('--tests/--no-tests', default=False)
@click.pass_obj
def init(obj, project_name, python_requires, import_name, repo_name, author,
         author_email, description, tests, docs, rtfd_name, importable,
         command, saythanks_to):
    env = {
        "author": author,
        "short_description": description,
        "saythanks_to": saythanks_to,
        "copyright_years": inspect_project.get_commit_years(Path()),
        "has_travis": tests,
        "has_docs": docs,
        "has_pypi": False,
        "has_doctests": False,
    }

    if import_name is not None:
        env["import_name"] = import_name
        env["is_flat_module"] = inspect_project.is_flat(Path(), import_name)
    else:
        env.update(inspect_project.find_module(Path()))

    if project_name is not None:
        env["project_name"] = project_name
    else:
        env["project_name"] = env["import_name"]

    if repo_name is not None:
        env["repo_name"] = repo_name
    else:
        ### TODO: If the repository has a GitHub remote, use that to set
        ### `repo_name`
        env["repo_name"] = env["project_name"]

    if rtfd_name is not None:
        env["rtfd_name"] = rtfd_name
    else:
        env["rtfd_name"] = project_name

    env["author_email"] = jinja_env().from_string(author_email)\
                                     .render(project_name=env["project_name"])

    try:
        with open('requirements.txt', encoding='utf-8') as fp:
            env["install_requires"] = list(yield_lines(fp))
    except FileNotFoundError:
        ### TODO: Check source file for __requires__ attribute (and then remove
        ### it)
        env["install_requires"] = []

    if re.fullmatch(r'\d+\.\d+', python_requires):
        python_requires = '~=' + python_requires
    env["python_requires"] = python_requires
    try:
        pyspec = SpecifierSet(python_requires)
    except ValueError:
        raise click.UsageError(
            f'Invalid specifier for --python-requires: {python_requires!r}'
        )
    env["python_versions"] = list(pyspec.filter(obj.pyversions))

    ### TODO: Support setting the entry point function name to something other
    ### than "main" on the command line
    ### TODO: Autodetect `if __name__ == '__main__':` lines in import_name.py /
    ### import_name/__main__.py and set `commands` accordingly
    if command is None:
        env["commands"] = {}
    elif env["is_flat_module"]:
        env["commands"] = {command: f'{env["import_name"]}:main'}
    else:
        env["commands"] = {command: f'{env["import_name"]}.__main__:main'}

    if importable is not None:
        env["importable"] = importable
    elif not env["install_requires"]:
        env["importable"] = True
    elif not env["is_flat_module"] \
            and (Path(env["import_name"]) / '__main__.py').exists():
        env["importable"] = True
    else:
        env["importable"] = False

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
    with InPlace(init_src, mode='t', encoding='utf-8') as fp:
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
        if not started:  # if init_src is empty
            print(jinja_env().get_template('init.j2').render(env), file=fp)
    util.runcmd('git', 'add', str(init_src))

    if Path('requirements.txt').exists():
        util.runcmd('git', 'rm', '-f', 'requirements.txt')


###def init_tests(env):
    ### tox.ini

###def init_travis(env):
    ### init_tests(env)
    ### .travis.yml, badges in README

###def init_docs(env):
    ### docs/*, tox.ini block, documentation URL in setup.cfg and README

def add_templated_file(filename, env):
    Path(filename).write_text(
        jinja_env().get_template(filename+'.j2').render(env).rstrip() + '\n',
        encoding='utf-8',
    )
    util.runcmd('git', 'add', filename)

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
