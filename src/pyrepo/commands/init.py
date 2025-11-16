import logging
from pathlib import Path
import re
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
from ..util import PyVersion, cpe_no_tb, ensure_license_years, runcmd

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
    command: str | None,
    description: str,
    docs: bool,
    doctests: bool,
    github_user: str | None,
    project_name: str,
    python_requires: str | None,
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

    log.info("Determining Python module ...")
    mod = find_module(dirpath)
    import_name = mod.import_name
    is_flat_module = mod.is_flat_module
    if is_flat_module:
        log.info("Found flat module %s.py", import_name)
    else:
        log.info("Found package %s", import_name)

    if not mod.src_layout and not mod.is_flat_module:
        log.info("Moving code to src/ directory ...")
        (dirpath / "src").mkdir(exist_ok=True)
        (dirpath / import_name).rename(dirpath / "src" / import_name)

    if is_flat_module and typing:
        log.info("Unflattening for py.typed file ...")
        pkgdir = dirpath / "src" / import_name
        pkgdir.mkdir(parents=True, exist_ok=True)
        (dirpath / f"{import_name}.py").rename(dirpath / pkgdir / "__init__.py")
        is_flat_module = False

    jenv = Environment()

    project_name = jenv.from_string(project_name).render(import_name=import_name)
    log.debug("Computed project name as %r", project_name)
    jenv_ctx = {"import_name": import_name, "project_name": project_name}

    repo_name = jenv.from_string(repo_name).render(jenv_ctx)
    log.debug("Computed repo name as %r", repo_name)

    rtfd_name = jenv.from_string(rtfd_name).render(jenv_ctx)
    log.debug("Computed RTFD name as %r", rtfd_name)

    author_email = jenv.from_string(author_email).render(jenv_ctx)
    log.debug("Computed author email as %r", author_email)

    log.info("Checking for requirements.txt ...")
    req_vars = parse_requirements(dirpath / "requirements.txt")

    if is_flat_module:
        initfile = dirpath / f"{import_name}.py"
        src_init = dirpath / "src" / f"{import_name}.py"
        if src_init.exists():
            src_init.rename(initfile)
            (dirpath / "src").rmdir()
    else:
        initfile = dirpath / "src" / import_name / "__init__.py"
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
    install_requires = [r for _, (r, _) in sorted(requirements.items())]

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

    try:
        pyspec = SpecifierSet(python_requires)
    except ValueError:
        raise click.UsageError(
            f"Invalid specifier for python_requires: {python_requires!r}"
        )
    python_versions = list(pyspec.filter(supported_pythons))
    if not python_versions:
        raise click.UsageError(
            f"No supported Python versions matching {python_requires!r}"
        )
    minver = python_versions[0]

    if command is None:
        commands = {}
    elif is_flat_module:
        commands = {command: f"{import_name}:main"}
    else:
        commands = {command: f"{import_name}.__main__:main"}

    extra_testenvs = {}
    if ci:
        extra_testenvs["lint"] = minver
        if typing:
            extra_testenvs["typing"] = minver

    project = Project(
        directory=dirpath,
        details=ProjectDetails(
            name=project_name,
            version="0.1.0.dev1",
            short_description=description,
            author=author,
            author_email=author_email,
            install_requires=install_requires,
            keywords=[],
            classifiers=[],
            supports_pypy=True,
            extra_testenvs=extra_testenvs,
            is_flat_module=is_flat_module,
            import_name=import_name,
            uses_versioningit=False,
            python_versions=list(map(PyVersion, python_versions)),
            python_requires=python_requires,
            commands=commands,
            github_user=github_user,
            repo_name=repo_name,
            rtfd_name=rtfd_name,
            has_tests=tests,
            has_typing=typing,
            has_doctests=doctests,
            has_docs=docs,
            has_ci=ci,
            has_pypi=False,
            copyright_years=repo.get_commit_years(),
            default_branch=repo.get_default_branch(),
        ),
    )

    twriter = project.get_template_writer()
    twriter.write(".gitignore", force=False)
    twriter.write(".pre-commit-config.yaml", force=False)
    twriter.write("README.rst", force=False)
    twriter.write("pyproject.toml", force=False)
    twriter.write("tox.ini", force=False)

    if project.details.has_typing:
        log.info("Creating src/%s/py.typed ...", project.details.import_name)
        (project.directory / "src" / project.details.import_name / "py.typed").touch()
    if project.details.has_ci:
        twriter.write(".github/dependabot.yml", force=False)
        twriter.write(".github/workflows/test.yml", force=False)
    if project.details.has_docs:
        twriter.write(".readthedocs.yaml", force=False)
        twriter.write("docs/index.rst", force=False)
        twriter.write("docs/conf.py", force=False)
        twriter.write("docs/requirements.txt", force=False)

    if (dirpath / "LICENSE").exists():
        log.info("Setting copyright year in LICENSE ...")
        ensure_license_years(dirpath / "LICENSE", project.details.copyright_years)
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
