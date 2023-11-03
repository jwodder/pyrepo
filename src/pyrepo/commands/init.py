import logging
from pathlib import Path
import re
from typing import Any, Optional
import click
from in_place import InPlace
from jinja2 import Environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name as normalize
from .. import git, util
from ..clack import ConfigurableCommand
from ..details import ProjectDetails
from ..gh import GitHub
from ..inspecting import extract_requires, find_module, parse_requirements
from ..project import Project
from ..util import cpe_no_tb, ensure_license_years, runcmd

log = logging.getLogger(__name__)


@click.command(cls=ConfigurableCommand)
@click.option(
    "--author", metavar="NAME", help="Project author's name", default="Anonymous"
)
@click.option(
    "--author-email",
    metavar="EMAIL",
    help="Project author's e-mail address",
    default="USER@HOST",
)
@click.option("--ci/--no-ci", help="Whether to generate CI configuration")
@click.option("--codecov-user", metavar="USER", help="Codecov.io username")
@click.option(
    "-c",
    "--command",
    metavar="NAME",
    help="Name of CLI command defined by project",
)
@click.option(
    "-d",
    "--description",
    prompt=True,
    help="Project's summary/short description",
)
@click.option(
    "--docs/--no-docs",
    help="Whether to generate Sphinx/RTD documentation boilerplate",
)
@click.option(
    "--doctests/--no-doctests",
    help="Whether to include running doctests in test configuration",
)
@click.option("--github-user", metavar="USER", help="Username of GitHub repository")
@click.option(
    "-p",
    "--project-name",
    metavar="NAME",
    help="Name of project",
    default="{{import_name}}",
)
@click.option(
    "-P",
    "--python-requires",
    metavar="SPEC",
    help="Python versions required by project",
)
@click.option(
    "--repo-name",
    metavar="NAME",
    help="Name of GitHub repository",
    default="{{project_name}}",
)
@click.option(
    "--rtfd-name",
    metavar="NAME",
    help="Name of RTFD.io site",
    default="{{project_name}}",
)
@click.option("--tests/--no-tests", help="Whether to generate test configuration")
@click.option(
    "--typing/--no-typing",
    help="Whether to configure for type annotations",
)
@click.argument(
    "dirpath",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
)
@click.pass_context
@cpe_no_tb
def cli(
    ctx: click.Context,
    dirpath: Path,
    author: str,
    author_email: str,
    ci: bool,
    codecov_user: Optional[str],
    command: Optional[str],
    description: str,
    docs: bool,
    doctests: bool,
    github_user: Optional[str],
    project_name: str,
    python_requires: Optional[str],
    repo_name: str,
    rtfd_name: str,
    tests: bool,
    typing: bool,
) -> None:
    """Create packaging boilerplate for a new project"""
    for fname in ["setup.py", "setup.cfg", "pyproject.toml"]:
        if (dirpath / fname).exists():
            raise click.UsageError(f"{fname} already exists")

    if github_user is None:
        with GitHub() as gh:
            github_user = gh.get("/user")["login"]

    repo = git.Git(dirpath=dirpath)

    env = {
        "author": author,
        "short_description": description,
        "copyright_years": repo.get_commit_years(),
        "has_doctests": doctests,
        "has_tests": tests or ci,
        "has_typing": typing,
        "has_ci": ci,
        "has_docs": docs,
        "has_pypi": False,
        "github_user": github_user,
        "codecov_user": none_or(codecov_user, github_user),
        "keywords": [],
        "classifiers": [],
        "version": "0.1.0.dev1",
        "supports_pypy": True,
        "extra_testenvs": {},
        "default_branch": repo.get_default_branch(),
        "uses_versioningit": False,
    }

    log.info("Determining Python module ...")
    mod = find_module(dirpath)
    env["import_name"] = mod.import_name
    env["is_flat_module"] = mod.is_flat_module
    if env["is_flat_module"]:
        log.info("Found flat module %s.py", env["import_name"])
    else:
        log.info("Found package %s", env["import_name"])

    if not mod.src_layout and not mod.is_flat_module:
        log.info("Moving code to src/ directory ...")
        (dirpath / "src").mkdir(exist_ok=True)
        code_path = env["import_name"]
        (dirpath / code_path).rename(dirpath / "src" / code_path)

    if env["is_flat_module"] and env["has_typing"]:
        log.info("Unflattening for py.typed file ...")
        pkgdir = dirpath / "src" / env["import_name"]
        pkgdir.mkdir(parents=True, exist_ok=True)
        (dirpath / f"{env['import_name']}.py").rename(dirpath / pkgdir / "__init__.py")
        env["is_flat_module"] = False

    jenv = Environment()

    env["name"] = jenv.from_string(project_name).render(import_name=env["import_name"])
    log.debug("Computed project name as %r", env["name"])
    jenv_ctx = {"import_name": env["import_name"], "project_name": env["name"]}

    env["repo_name"] = jenv.from_string(repo_name).render(jenv_ctx)
    log.debug("Computed repo name as %r", env["repo_name"])

    env["rtfd_name"] = jenv.from_string(rtfd_name).render(jenv_ctx)
    log.debug("Computed RTFD name as %r", env["rtfd_name"])

    env["author_email"] = jenv.from_string(author_email).render(jenv_ctx)
    log.debug("Computed author email as %r", env["author_email"])

    log.info("Checking for requirements.txt ...")
    req_vars = parse_requirements(dirpath / "requirements.txt")

    if env["is_flat_module"]:
        initfile = dirpath / f"{env['import_name']}.py"
    else:
        initfile = dirpath / "src" / env["import_name"] / "__init__.py"
    log.info("Checking for __requires__ ...")
    src_vars = extract_requires(initfile)

    requirements = {}
    for r in (req_vars.requires or []) + (src_vars.requires or []):
        req = Requirement(r)
        name = normalize(req.name)
        # `Requirement` objects don't have an `__eq__`, so we need to convert
        # them to `str` in order to compare them.
        reqstr = str(req)
        if name not in requirements:
            requirements[name] = (r, reqstr)
        elif reqstr != requirements[name][1]:
            raise click.UsageError(
                f"Two different requirements for {name} found:"
                f" {requirements[name][0]!r} and {r!r}"
            )
    env["install_requires"] = [r for _, (r, _) in sorted(requirements.items())]

    supported_pythons = util.cpython_supported()

    if (
        python_requires is not None
        and ctx.get_parameter_source("python_requires")
        is not click.core.ParameterSource.DEFAULT_MAP
    ):
        if re.fullmatch(r"\d+\.\d+", python_requires):
            python_requires = f">={python_requires}"
    else:
        pyreq_req = req_vars.python_requires
        pyreq_src = src_vars.python_requires
        if pyreq_req is not None and pyreq_src is not None:
            if SpecifierSet(pyreq_req) != SpecifierSet(pyreq_src):
                raise click.UsageError(
                    f"Two different Python requirements found:"
                    f" {pyreq_req!r} and {pyreq_src!r}"
                )
            python_requires = pyreq_req
        elif pyreq_req is not None:
            python_requires = pyreq_req
        elif pyreq_src is not None:
            python_requires = pyreq_src
        elif python_requires is None:
            python_requires = f">={supported_pythons[0]}"

    env["python_requires"] = python_requires
    try:
        pyspec = SpecifierSet(python_requires)
    except ValueError:
        raise click.UsageError(
            f"Invalid specifier for python_requires: {python_requires!r}"
        )
    env["python_versions"] = list(pyspec.filter(supported_pythons))
    if not env["python_versions"]:
        raise click.UsageError(
            f"No supported Python versions matching {python_requires!r}"
        )
    minver = env["python_versions"][0]

    if command is None:
        env["commands"] = {}
    elif env["is_flat_module"]:
        env["commands"] = {command: f'{env["import_name"]}:main'}
    else:
        env["commands"] = {command: f'{env["import_name"]}.__main__:main'}

    if env["has_ci"]:
        env["extra_testenvs"]["lint"] = minver
        if env["has_typing"]:
            env["extra_testenvs"]["typing"] = minver

    project = Project(directory=dirpath, details=ProjectDetails.parse_obj(env))
    twriter = project.get_template_writer()
    twriter.write(".gitignore", force=False)
    twriter.write(".pre-commit-config.yaml", force=False)
    twriter.write("README.rst", force=False)
    twriter.write("pyproject.toml", force=False)
    twriter.write("tox.ini", force=False)

    if env["has_typing"]:
        log.info("Creating src/%s/py.typed ...", env["import_name"])
        (project.directory / "src" / env["import_name"] / "py.typed").touch()
    if env["has_ci"]:
        twriter.write(".github/dependabot.yml", force=False)
        twriter.write(".github/workflows/test.yml", force=False)
    if env["has_docs"]:
        twriter.write(".readthedocs.yaml", force=False)
        twriter.write("docs/index.rst", force=False)
        twriter.write("docs/conf.py", force=False)
        twriter.write("docs/requirements.txt", force=False)

    if (dirpath / "LICENSE").exists():
        log.info("Setting copyright year in LICENSE ...")
        ensure_license_years(dirpath / "LICENSE", env["copyright_years"])
    else:
        twriter.write("LICENSE", force=False)

    log.info("Adding intro block to initfile ...")
    with InPlace(initfile, mode="t", encoding="utf-8") as fp:
        started = False
        for line in fp:
            if line.startswith("#!") or (
                line.lstrip().startswith("#")
                and re.search(r"coding[=:]\s*([-\w.]+)", line)
            ):
                pass
            elif not started:
                print(twriter.render("init"), file=fp)
                started = True
            print(line, file=fp, end="")
        if not started:  # if initfile is empty
            print(twriter.render("init"), file=fp, end="")

    (dirpath / "requirements.txt").unlink(missing_ok=True)

    runcmd("pre-commit", "install", cwd=dirpath)
    log.info("TODO: Run `pre-commit run -a` after adding new files")


def none_or(x: Any, y: Any) -> Any:
    return x if x is not None else y
