from contextlib import suppress
import logging
from pathlib import Path
import re
from typing import Any
import click
from in_place import InPlace
from jinja2 import Environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name as normalize
from .. import git, inspecting
from ..config import Config
from ..project import Project
from ..util import PyVersion, cpe_no_tb, ensure_license_years, optional, runcmd

log = logging.getLogger(__name__)


@click.command()
@optional("--author", metavar="NAME", help="Project author's name")
@optional(
    "--author-email",
    metavar="EMAIL",
    help="Project author's e-mail address",
)
@optional("--ci/--no-ci", help="Whether to generate CI configuration")
@optional("--codecov-user", metavar="USER", help="Codecov.io username")
@optional(
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
@optional(
    "--docs/--no-docs",
    help="Whether to generate Sphinx/RTD documentation boilerplate",
)
@optional(
    "--doctests/--no-doctests",
    help="Whether to include running doctests in test configuration",
)
@optional("--github-user", metavar="USER", help="Username of GitHub repository")
@optional("-p", "--project-name", metavar="NAME", help="Name of project")
@optional(
    "-P",
    "--python-requires",
    metavar="SPEC",
    help="Python versions required by project",
)
@optional("--repo-name", metavar="NAME", help="Name of GitHub repository")
@optional("--rtfd-name", metavar="NAME", help="Name of RTFD.io site")
@optional("--tests/--no-tests", help="Whether to generate test configuration")
@optional(
    "--typing/--no-typing",
    help="Whether to configure for type annotations",
)
@click.argument(
    "dirpath",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path(),
)
@click.pass_obj
@cpe_no_tb
def cli(obj: Config, dirpath: Path, **options: Any) -> None:
    """Create packaging boilerplate for a new project"""
    if (dirpath / "setup.py").exists():
        raise click.UsageError("setup.py already exists")
    if (dirpath / "setup.cfg").exists():
        raise click.UsageError("setup.cfg already exists")
    if (dirpath / "pyproject.toml").exists():
        raise click.UsageError("pyproject.toml already exists")

    defaults = obj.defaults["init"]
    pyreq_cfg = defaults.pop("python_requires")
    options = dict(defaults, **options)

    if "github_user" not in options:
        options["github_user"] = obj.gh.user.get()["login"]

    repo = git.Git(dirpath=dirpath)

    env = {
        "author": options["author"],
        "short_description": options["description"],
        "copyright_years": repo.get_commit_years(),
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
        "default_branch": repo.get_default_branch(),
        "uses_versioningit": False,
    }

    log.info("Determining Python module ...")
    # "import_name", "is_flat_module", and "src_layout"
    env.update(inspecting.find_module(dirpath).dict())
    if env["is_flat_module"]:
        log.info("Found flat module %s.py", env["import_name"])
    else:
        log.info("Found package %s", env["import_name"])

    if not env.pop("src_layout", False):
        log.info("Moving code to src/ directory ...")
        (dirpath / "src").mkdir(exist_ok=True)
        code_path = env["import_name"]
        if env["is_flat_module"]:
            code_path += ".py"
        (dirpath / code_path).rename(dirpath / "src" / code_path)

    if env["is_flat_module"] and env["has_typing"]:
        log.info("Unflattening for py.typed file ...")
        pkgdir = dirpath / "src" / env["import_name"]
        pkgdir.mkdir(parents=True, exist_ok=True)
        (dirpath / "src" / (env["import_name"] + ".py")).rename(
            dirpath / pkgdir / "__init__.py"
        )
        env["is_flat_module"] = False

    env["name"] = options.get("project_name", env["import_name"])
    env["repo_name"] = options.get("repo_name", env["name"])
    env["rtfd_name"] = options.get("rtfd_name", env["name"])

    env["author_email"] = (
        Environment()
        .from_string(options["author_email"])
        .render(project_name=env["name"])
    )

    log.info("Checking for requirements.txt ...")
    req_vars = inspecting.parse_requirements(dirpath / "requirements.txt")

    if env["is_flat_module"]:
        initfile = dirpath / "src" / (env["import_name"] + ".py")
    else:
        initfile = dirpath / "src" / env["import_name"] / "__init__.py"
    log.info("Checking for __requires__ ...")
    src_vars = inspecting.extract_requires(initfile)

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

    python_requires = options.get("python_requires")
    if python_requires is not None:
        if re.fullmatch(r"\d+\.\d+", python_requires):
            python_requires = "~=" + python_requires
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
        else:
            python_requires = pyreq_cfg

    env["python_requires"] = python_requires
    try:
        pyspec = SpecifierSet(python_requires)
    except ValueError:
        raise click.UsageError(
            f"Invalid specifier for python_requires: {python_requires!r}"
        )
    env["python_versions"] = list(pyspec.filter(obj.pyversions))
    if not env["python_versions"]:
        raise click.UsageError(
            f"No Python versions in pyversions range matching {python_requires!r}"
        )
    minver = str(min(env["python_versions"], key=PyVersion.parse))

    if "command" not in options:
        env["commands"] = {}
    elif env["is_flat_module"]:
        env["commands"] = {options["command"]: f'{env["import_name"]}:main'}
    else:
        env["commands"] = {options["command"]: f'{env["import_name"]}.__main__:main'}

    if env["has_ci"]:
        env["extra_testenvs"]["lint"] = minver
        if env["has_typing"]:
            env["extra_testenvs"]["typing"] = minver

    project = Project(directory=dirpath, details=env)
    twriter = project.get_template_writer()
    twriter.write(".gitignore", force=False)
    twriter.write(".pre-commit-config.yaml", force=False)
    twriter.write("MANIFEST.in", force=False)
    twriter.write("README.rst", force=False)
    twriter.write("pyproject.toml", force=False)
    twriter.write("setup.cfg", force=False)
    twriter.write("tox.ini", force=False)

    if env["has_typing"]:
        log.info("Creating src/%s/py.typed ...", env["import_name"])
        (project.directory / "src" / env["import_name"] / "py.typed").touch()
    if env["has_ci"]:
        twriter.write(".github/workflows/test.yml", force=False)
    if env["has_docs"]:
        twriter.write(".readthedocs.yml", force=False)
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

    with suppress(FileNotFoundError):
        (dirpath / "requirements.txt").unlink()

    runcmd("pre-commit", "install", cwd=dirpath)
    log.info("TODO: Run `pre-commit run -a` after adding new files")
