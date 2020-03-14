#!/usr/bin/python3
from   pathlib              import Path
import re
import click
from   in_place               import InPlace
from   packaging.requirements import Requirement
from   packaging.specifiers   import SpecifierSet
from   packaging.utils        import canonicalize_name as normalize
from   ..                     import inspecting, util

@click.command()
@util.optional('--author', metavar='NAME')
@util.optional('--author-email', metavar='EMAIL')
@util.optional('--codecov-user', metavar='USER')
@util.optional('-c', '--command', metavar='NAME')
@click.option('-d', '--description', prompt=True)
@util.optional('--docs/--no-docs')
@util.optional('--github-user', metavar='USER')
@click.option('--importable/--no-importable', default=None)
@util.optional('-p', '--project-name', metavar='NAME')
@util.optional('-P', '--python-requires', metavar='SPEC')
@util.optional('--repo-name', metavar='NAME')
@util.optional('--rtfd-name', metavar='NAME')
@util.optional('--saythanks-to', metavar='USER')
@util.optional('--tests/--no-tests')
@util.optional('--travis/--no-travis')
@util.optional('--travis-user', metavar='USER')
@click.pass_obj
def cli(obj, **options):
    if Path('setup.py').exists():
        raise click.UsageError('setup.py already exists')
    if Path('setup.cfg').exists():
        raise click.UsageError('setup.cfg already exists')

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
    }

    # "import_name" and "is_flat_module"
    env.update(inspecting.find_module(Path()))

    env["project_name"] = options.get("project_name", env["import_name"])
    env["repo_name"] = options.get("repo_name", env["project_name"])
    env["rtfd_name"] = options.get("rtfd_name", env["project_name"])

    env["author_email"] = util.jinja_env().from_string(options["author_email"])\
                                          .render(
                                            project_name=env["project_name"]
                                          )

    req_vars = inspecting.parse_requirements('requirements.txt')

    if env["is_flat_module"]:
        init_src = Path(env["import_name"] + '.py')
    else:
        init_src = Path(env["import_name"]) / '__init__.py'
    src_vars = inspecting.extract_requires(init_src)

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

    if options["importable"] is not None:
        env["importable"] = options["importable"]
    elif not env["install_requires"]:
        env["importable"] = True
    elif not env["is_flat_module"] \
            and (Path(env["import_name"]) / '__main__.py').exists():
        env["importable"] = True
    else:
        env["importable"] = False

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
            add_templated_file(filename, env)

    if Path('LICENSE').exists():
        util.ensure_license_years('LICENSE', env["copyright_years"])
    else:
        add_templated_file('LICENSE', env)

    with InPlace(init_src, mode='t', encoding='utf-8') as fp:
        started = False
        for line in fp:
            if line.startswith('#!') \
                or (line.lstrip().startswith('#')
                    and re.search(r'coding[=:]\s*([-\w.]+)', line)):
                pass
            elif not started:
                print(
                    util.jinja_env().get_template('init.j2').render(env),
                    file=fp,
                )
                print(file=fp)
                started = True
            print(line, file=fp, end='')
        if not started:  # if init_src is empty
            print(util.jinja_env().get_template('init.j2').render(env), file=fp)

    try:
        Path('requirements.txt').unlink()
    except FileNotFoundError:
        pass


def add_templated_file(filename, env):
    Path(filename).write_text(
        util.jinja_env().get_template(filename+'.j2').render(env).rstrip()
            + '\n',
        encoding='utf-8',
    )
