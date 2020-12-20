from   contextlib             import suppress
import logging
from   pathlib                import Path
import re
import click
from   in_place               import InPlace
from   packaging.requirements import Requirement
from   packaging.specifiers   import SpecifierSet
from   packaging.utils        import canonicalize_name as normalize
from   ..                     import inspecting
from   ..project              import Project
from   ..util                 import ensure_license_years, get_jinja_env, \
                                        optional

log = logging.getLogger(__name__)

@click.command()
@optional('--author', metavar='NAME')
@optional('--author-email', metavar='EMAIL')
@optional('--ci/--no-ci')
@optional('--codecov-user', metavar='USER')
@optional('-c', '--command', metavar='NAME')
@click.option('-d', '--description', prompt=True)
@optional('--docs/--no-docs')
@optional('--doctests/--no-doctests')
@optional('--github-user', metavar='USER')
@optional('-p', '--project-name', metavar='NAME')
@optional('-P', '--python-requires', metavar='SPEC')
@optional('--repo-name', metavar='NAME')
@optional('--rtfd-name', metavar='NAME')
@optional('--tests/--no-tests')
@optional('--typing/--no-typing')
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
        "copyright_years": inspecting.get_commit_years(Path()),
        "has_doctests": options.get("doctests", False),
        "has_tests": options.get("tests", False) or options.get("ci", False),
        "has_typing": options.get("typing", False),
        "has_ci": options.get("ci", False),
        "has_docs": options.get("docs", False),
        "has_pypi": False,
        "github_user": options["github_user"],
        "codecov_user": options.get("codecov_user", options["github_user"]),
        "keywords": [],
        "version": "0.1.0.dev1",
        "supports_pypy3": True,
        "extra_testenvs": {},
    }

    log.info("Determining Python module ...")
    # "import_name", "is_flat_module", and "src_layout"
    env.update(inspecting.find_module(Path()))
    if env["is_flat_module"]:
        log.info("Found flat module %s.py", env["import_name"])
    else:
        log.info("Found package %s", env["import_name"])

    if not env.pop("src_layout", False):
        log.info("Moving code to src/ directory ...")
        Path("src").mkdir(exist_ok=True)
        code_path = env["import_name"]
        if env["is_flat_module"]:
            code_path += '.py'
        Path(code_path).rename(Path("src", code_path))

    if env["is_flat_module"] and env["has_typing"]:
        log.info("Unflattening for py.typed file ...")
        pkgdir = Path("src", env["import_name"])
        pkgdir.mkdir(parents=True, exist_ok=True)
        Path("src", env["import_name"] + ".py").rename(pkgdir / "__init__.py")
        env["is_flat_module"] = False

    env["project_name"] = options.get("project_name", env["import_name"])
    env["repo_name"] = options.get("repo_name", env["project_name"])
    env["rtfd_name"] = options.get("rtfd_name", env["project_name"])

    jenv = get_jinja_env()

    env["author_email"] = jenv.from_string(options["author_email"])\
                              .render(project_name=env["project_name"])

    log.info("Checking for requirements.txt ...")
    req_vars = inspecting.parse_requirements('requirements.txt')

    if env["is_flat_module"]:
        initfile = Path("src", env["import_name"] + '.py')
    else:
        initfile = Path("src", env["import_name"], '__init__.py')
    log.info("Checking for __requires__ ...")
    src_vars = inspecting.extract_requires(initfile)

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

    project = Project.from_inspection(Path(), env)
    project.write_template(".gitignore", jenv, force=False)
    project.write_template("MANIFEST.in", jenv, force=False)
    project.write_template("README.rst", jenv, force=False)
    project.write_template("pyproject.toml", jenv, force=False)
    project.write_template("setup.cfg", jenv, force=False)

    if env["has_tests"] or env["has_docs"]:
        project.write_template('tox.ini', jenv, force=False)
    if env["has_typing"]:
        log.info("Creating src/%s/py.typed ...", env["import_name"])
        (project.directory / "src" / env["import_name"] / "py.typed").touch()
    if env["has_ci"]:
        if env["has_typing"]:
            project.extra_testenvs["typing"] = project.python_versions[0]
        project.write_template('.github/workflows/test.yml', jenv, force=False)
    if env["has_docs"]:
        project.write_template('.readthedocs.yml', jenv, force=False)
        project.write_template('docs/index.rst', jenv, force=False)
        project.write_template('docs/conf.py', jenv, force=False)
        project.write_template('docs/requirements.txt', jenv, force=False)

    if Path('LICENSE').exists():
        log.info("Setting copyright year in LICENSE ...")
        ensure_license_years('LICENSE', env["copyright_years"])
    else:
        project.write_template("LICENSE", jenv, force=False)

    log.info("Adding intro block to initfile ...")
    with InPlace(initfile, mode='t', encoding='utf-8') as fp:
        started = False
        for line in fp:
            if line.startswith('#!') \
                or (line.lstrip().startswith('#')
                    and re.search(r'coding[=:]\s*([-\w.]+)', line)):
                pass
            elif not started:
                print(jenv.get_template('init.j2').render(env), file=fp)
                print(file=fp)
                started = True
            print(line, file=fp, end='')
        if not started:  # if initfile is empty
            print(jenv.get_template('init.j2').render(env), file=fp)

    with suppress(FileNotFoundError):
        Path('requirements.txt').unlink()
