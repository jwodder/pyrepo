import os.path
from   pathlib                import Path
import re
import click
from   in_place               import InPlace
from   packaging.requirements import Requirement
from   packaging.specifiers   import SpecifierSet
from   packaging.utils        import canonicalize_name as normalize
from   ..                     import inspecting
from   ..util                 import ensure_license_years, optional

@click.command()
@optional('--author', metavar='NAME')
@optional('--author-email', metavar='EMAIL')
@optional('--codecov-user', metavar='USER')
@optional('-c', '--command', metavar='NAME')
@click.option('-d', '--description', prompt=True)
@optional('--docs/--no-docs')
@optional('--github-user', metavar='USER')
@optional('-p', '--project-name', metavar='NAME')
@optional('-P', '--python-requires', metavar='SPEC')
@optional('--repo-name', metavar='NAME')
@optional('--rtfd-name', metavar='NAME')
@optional('--saythanks-to', metavar='USER')
@optional('--tests/--no-tests')
@optional('--travis/--no-travis')
@optional('--travis-user', metavar='USER')
@click.pass_obj
def cli(obj, **options):
    if Path('setup.py').exists():
        raise click.UsageError('setup.py already exists')
    if Path('setup.cfg').exists():
        raise click.UsageError('setup.cfg already exists')
    if Path('pyproject.toml').exists():
        raise click.UsageError('pyproject.toml already exists')

    defaults = obj.defaults['init']
    pyreq_cfg = defaults.pop("python_requires")
    options = dict(defaults, **options)

    if "github_user" not in options:
        options["github_user"] = obj.gh.user.get()["login"]

    env = {
        "author": options["author"],
        "short_description": options["description"],
        "saythanks_to": options.get("saythanks_to"),
        "copyright_years": inspecting.get_commit_years(Path()),
        "has_tests": options.get("tests",False) or options.get("travis",False),
        "has_travis": options.get("travis", False),
        "has_docs": options.get("docs", False),
        "has_pypi": False,
        "github_user": options["github_user"],
        "travis_user": options.get("travis_user", options["github_user"]),
        "codecov_user": options.get("codecov_user", options["github_user"]),
        "keywords": [],
        "version": "0.1.0.dev1",
        "pep517": False,
    }

    # "import_name", "is_flat_module", and "src_layout"
    env.update(inspecting.find_module(Path()))

    env["project_name"] = options.get("project_name", env["import_name"])
    env["repo_name"] = options.get("repo_name", env["project_name"])
    env["rtfd_name"] = options.get("rtfd_name", env["project_name"])

    env["author_email"] = obj.jinja_env.from_string(options["author_email"])\
                                       .render(project_name=env["project_name"])

    req_vars = inspecting.parse_requirements('requirements.txt')

    if env["is_flat_module"]:
        init_src = [env["import_name"] + '.py']
    else:
        init_src = [env["import_name"], '__init__.py']
    if env["src_layout"]:
        init_src.insert(0, 'src')
    env["initfile"] = os.path.join(*init_src)
    src_vars = inspecting.extract_requires(env["initfile"])

    requirements = {}
    for r in (req_vars["__requires__"] or []) \
            + (src_vars["__requires__"] or []):
        req = Requirement(r)
        name = normalize(req.name)
        # `Requirement` objects don't have an `__eq__`, so we need to convert
        # them to `str` in order to compare them.
        req = str(req)
        if name not in requirements:
            requirements[name] = (r, req)
        elif req != requirements[name][1]:
            raise click.UsageError(
                f'Two different requirements for {name} found:'
                f' {requirements[name][0]!r} and {r!r}'
            )
    env["install_requires"] = [r for _,(r,_) in sorted(requirements.items())]

    python_requires = options.get("python_requires")
    if python_requires is not None:
        if re.fullmatch(r'\d+\.\d+', python_requires):
            python_requires = '~=' + python_requires
    else:
        pyreq_req = req_vars["__python_requires__"]
        pyreq_src = src_vars["__python_requires__"]
        if pyreq_req is not None and pyreq_src is not None:
            if SpecifierSet(pyreq_req) != SpecifierSet(pyreq_src):
                raise click.UsageError(
                    f'Two different Python requirements found:'
                    f' {pyreq_req!r} and {pyreq_src!r}'
                )
            python_requires = pyreq_req
        elif pyreq_req is not None:
            python_requires = pyreq_req
        elif pyreq_src is not None:
            python_requires = pyreq_src
        else:
            python_requires = pyreq_cfg

    env["python_requires"] = python_requires
    try:
        pyspec = SpecifierSet(python_requires)
    except ValueError:
        raise click.UsageError(
            f'Invalid specifier for python_requires: {python_requires!r}'
        )
    env["python_versions"] = list(pyspec.filter(obj.pyversions))

    if "command" not in options:
        env["commands"] = {}
    elif env["is_flat_module"]:
        env["commands"] = {options["command"]: f'{env["import_name"]}:main'}
    else:
        env["commands"] = {
            options["command"]: f'{env["import_name"]}.__main__:main'
        }

    templated = [
        '.gitignore', 'MANIFEST.in', 'README.rst', 'setup.cfg', 'setup.py',
    ]
    if env["has_tests"] or env["has_docs"]:
        templated.append('tox.ini')
    if env["has_travis"]:
        templated.append('.travis.yml')
    if env["has_docs"]:
        Path('docs').mkdir(exist_ok=True)
        templated.extend([
            'docs/index.rst',
            'docs/conf.py',
            'docs/requirements.txt',
        ])

    for filename in templated:
        if not Path(filename).exists():
            add_templated_file(obj.jinja_env, filename, env)

    if Path('LICENSE').exists():
        ensure_license_years('LICENSE', env["copyright_years"])
    else:
        add_templated_file(obj.jinja_env, 'LICENSE', env)

    with InPlace(env["initfile"], mode='t', encoding='utf-8') as fp:
        started = False
        for line in fp:
            if line.startswith('#!') \
                or (line.lstrip().startswith('#')
                    and re.search(r'coding[=:]\s*([-\w.]+)', line)):
                pass
            elif not started:
                print(
                    obj.jinja_env.get_template('init.j2').render(env),
                    file=fp,
                )
                print(file=fp)
                started = True
            print(line, file=fp, end='')
        if not started:  # if initfile is empty
            print(obj.jinja_env.get_template('init.j2').render(env), file=fp)

    try:
        Path('requirements.txt').unlink()
    except FileNotFoundError:
        pass


def add_templated_file(jinja_env, filename, env):
    Path(filename).write_text(
        jinja_env.get_template(filename+'.j2').render(env).rstrip() + '\n',
        encoding='utf-8',
    )
