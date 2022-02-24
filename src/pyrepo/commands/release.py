# TODO:
# - Try to give this some level of idempotence
# - Add options/individual commands for doing each release step separately

# External dependencies:
# - git (including push access to repository)
# - gpg (including a key usable for signing)
# - PyPI credentials for twine
# - GitHub OAuth token in config

# Notable assumptions made by this code:
# - There is no CHANGELOG file until after the initial release has been made.

from datetime import date
from functools import partial
import logging
from mimetypes import add_type, guess_type
import os
import os.path
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
from typing import Any, Callable, List, Optional, Sequence
import click
from configupdater import ConfigUpdater
from in_place import InPlace
from linesep import read_paragraphs
from packaging.version import Version
from pydantic import BaseModel, Field
from uritemplate import expand
from ..config import Config
from ..gh import GitHub
from ..project import Project, with_project
from ..util import (
    Bump,
    bump_version,
    cpe_no_tb,
    ensure_license_years,
    map_lines,
    replace_group,
    runcmd,
    update_years2str,
)

log = logging.getLogger(__name__)

ACTIVE_BADGE = """\
.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.
"""


class Releaser(BaseModel):
    project: Project
    version: str
    ghrepo: GitHub
    tox: bool
    sign_assets: bool
    assets: List[Path] = Field(default_factory=list)
    assets_asc: List[Path] = Field(default_factory=list)
    release_upload_url: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_project(
        cls,
        project: Project,
        gh: GitHub,
        version: Optional[str] = None,
        tox: bool = False,
        sign_assets: bool = False,
    ) -> "Releaser":
        if version is None:
            # Remove prerelease & dev release from __version__
            v = Version(project.details.version).base_version
        else:
            v = version.lstrip("v")
        return cls(
            project=project,
            version=v,
            ghrepo=gh.repos[project.details.github_user][project.details.repo_name],
            tox=tox,
            sign_assets=sign_assets,
        )

    def run(self) -> None:
        self.end_dev()
        if self.tox:
            self.tox_check()
        if not self.project.details.uses_versioningit:
            self.build(sign_assets=self.sign_assets)
            self.twine_check()
        self.commit_version()
        if self.project.details.uses_versioningit:
            self.build(sign_assets=self.sign_assets)
            self.twine_check()
        self.project.repo.run("push", "--follow-tags")
        self.mkghrelease()
        self.upload()
        self.project.begin_dev()  # Not idempotent

    def tox_check(self) -> None:  # Idempotent
        if (self.project.directory / "tox.ini").exists():
            log.info("Running tox ...")
            runcmd("tox", cwd=self.project.directory)

    def twine_check(self) -> None:  # Idempotent
        log.info("Running twine check ...")
        assert self.assets, "Nothing to check"
        runcmd(sys.executable, "-m", "twine", "check", "--strict", *self.assets)

    def commit_version(self) -> None:  ### Not idempotent
        log.info("Committing & tagging ...")
        # We need to create a temporary file instead of just passing the commit
        # message on stdin because `git commit`'s `--template` option doesn't
        # support reading from stdin.
        with NamedTemporaryFile(mode="w+", encoding="utf-8") as tmplate:
            # When using `--template`, Git requires the user to make *some*
            # change to the commit message or it'll abort the commit, so add in
            # a line to delete:
            print("DELETE THIS LINE", file=tmplate)
            print(file=tmplate)
            chlog = self.project.get_changelog()
            if chlog and chlog.sections:
                print(f"v{self.version} — INSERT SHORT DESCRIPTION HERE", file=tmplate)
                print(file=tmplate)
                print("INSERT LONG DESCRIPTION HERE (optional)", file=tmplate)
                print(file=tmplate)
                print("CHANGELOG:", file=tmplate)
                print(file=tmplate)
                print(chlog.sections[0].content, file=tmplate)
            else:
                print(f"v{self.version} — Initial release", file=tmplate)
            print(file=tmplate)
            print("# Write in Markdown.", file=tmplate)
            print("# The first line will be used as the release name.", file=tmplate)
            print("# The rest will be used as the release body.", file=tmplate)
            tmplate.flush()
            self.project.repo.run("commit", "-a", "-v", "--template", tmplate.name)
        self.project.repo.run(
            "tag",
            "-s",
            "-m",
            "Version " + self.version,
            "v" + self.version,
            env={**os.environ, "GPG_TTY": os.ttyname(0)},
        )

    def mkghrelease(self) -> None:  ### Not idempotent
        log.info("Creating GitHub release ...")
        subject, body = self.project.repo.read(
            "show",
            "-s",
            "--format=%s%x00%b",
            "v" + self.version + "^{commit}",
        ).split("\0", 1)
        reldata = self.ghrepo.releases.post(
            json={
                "tag_name": "v" + self.version,
                "name": subject,
                "body": body.strip(),  ### TODO: Remove line wrapping?
                "draft": False,
            }
        )
        self.release_upload_url = reldata["upload_url"]

    def build(self, sign_assets: bool = False) -> None:  ### Not idempotent
        log.info("Building artifacts ...")
        self.project.build(clean=True)
        self.assets = []
        self.assets_asc = []
        signer: Optional[Callable[[str], Any]]
        if sign_assets:
            gpg_program = self.project.repo.get_config("gpg.program", default="gpg")
            assert gpg_program is not None
            signer = partial(
                runcmd,
                gpg_program,
                "--detach-sign",
                "-a",
                env={**os.environ, "GPG_TTY": os.ttyname(0)},
            )
        else:
            signer = None
        for distfile in (self.project.directory / "dist").iterdir():
            self.assets.append(distfile)
            if signer is not None:
                signer(distfile)  # type: ignore[unreachable]
                self.assets_asc.append(distfile.with_name(distfile.name + ".asc"))

    def upload(self) -> None:
        log.info("Uploading artifacts ...")
        assert self.assets, "Nothing to upload"
        self.upload_pypi()
        self.upload_github()

    def upload_pypi(self) -> None:  # Idempotent
        log.info("Uploading artifacts to PyPI ...")
        runcmd(
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--skip-existing",
            *(self.assets + self.assets_asc),
        )

    def upload_github(self) -> None:  ### Not idempotent
        log.info("Uploading artifacts to GitHub release ...")
        assert (
            self.release_upload_url is not None
        ), "Cannot upload to GitHub before creating release"
        for asset in self.assets:
            url = expand(self.release_upload_url, name=asset.name, label=None)
            self.ghrepo[url].post(
                headers={"Content-Type": get_mime_type(asset.name)},
                data=asset.read_bytes(),
            )

    def end_dev(self) -> None:  # Idempotent
        log.info("Finalizing version ...")
        self.project.set_version(self.version)
        # Set release date in CHANGELOGs
        for docs in (False, True):
            if docs:
                log.info("Updating docs/changelog.rst ...")
            else:
                log.info("Updating CHANGELOG ...")
            chlog = self.project.get_changelog(docs=docs)
            if chlog and chlog.sections:
                chlog.sections[0].version = f"v{self.version}"
                chlog.sections[0].release_date = date.today()
                self.project.set_changelog(chlog, docs=docs)
        years = self.project.repo.get_commit_years()
        # Update year ranges in LICENSE
        log.info("Ensuring LICENSE copyright line is up to date ...")
        ensure_license_years(self.project.directory / "LICENSE", years)
        # Update year ranges in docs/conf.py
        docs_conf = self.project.directory / "docs" / "conf.py"
        if docs_conf.exists():
            log.info("Ensuring docs/conf.py copyright is up to date ...")
            map_lines(
                docs_conf,
                partial(
                    replace_group,
                    r'^copyright\s*=\s*[\x27"](\d[-,\d\s]+\d) \w+',
                    lambda ys: update_years2str(ys, years),
                ),
            )
        if self.project.get_changelog() is None:
            # Initial release
            self.end_initial_dev()

    def end_initial_dev(self) -> None:  # Idempotent
        # Set repostatus to "Active":
        log.info("Advancing repostatus ...")
        ### TODO: Use the Readme class for this:
        with InPlace(
            self.project.directory / "README.rst",
            mode="t",
            encoding="utf-8",
        ) as fp:
            for para in read_paragraphs(fp):
                if para.splitlines()[0] == (
                    ".. image:: http://www.repostatus.org/badges/latest/wip.svg"
                ):
                    print(ACTIVE_BADGE, file=fp)
                else:
                    print(para, file=fp, end="")
        # Set "Development Status" classifier to "Beta" or higher:
        log.info("Advancing Development Status classifier ...")
        advance_devstatus(self.project.directory / "setup.cfg")
        log.info("Updating GitHub topics ...")
        ### TODO: Check that the repository has topics first?
        self.update_gh_topics(
            add=["available-on-pypi"],
            remove=["work-in-progress"],
        )

    def update_gh_topics(
        self, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None:
        topics = set(self.ghrepo.get()["topics"])
        new_topics = topics.union(add).difference(remove)
        if new_topics != topics:
            self.ghrepo.topics.put(json={"names": list(new_topics)})


@click.command()
@click.option("--tox/--no-tox", default=None, help="Run tox before building")
@click.option(
    "--sign-assets/--no-sign-assets", default=None, help="Sign built assets with PGP"
)
@click.option(
    "--major",
    "bump",
    flag_value=Bump.MAJOR,
    type=click.UNPROCESSED,
    help="Release the next major version",
)
@click.option(
    "--minor",
    "bump",
    flag_value=Bump.MINOR,
    type=click.UNPROCESSED,
    help="Release the next minor version",
)
@click.option(
    "--micro",
    "bump",
    flag_value=Bump.MICRO,
    type=click.UNPROCESSED,
    help="Release the next micro/patch version",
)
@click.option(
    "--patch",
    "bump",
    flag_value=Bump.MICRO,
    type=click.UNPROCESSED,
    help="Release the next micro/patch version",
)
@click.option(
    "--post",
    "bump",
    flag_value=Bump.POST,
    type=click.UNPROCESSED,
    help="Release the next post version",
)
@click.option(
    "--date",
    "bump",
    flag_value=Bump.DATE,
    type=click.UNPROCESSED,
    help="Release a date-versioned version",
)
@click.argument("version", required=False)
@click.pass_obj
@with_project
@cpe_no_tb
def cli(
    obj: Config,
    project: Project,
    version: Optional[str],
    tox: Optional[bool],
    sign_assets: Optional[bool],
    bump: Optional[Bump],
) -> None:
    """Make a new release of the project"""
    defaults = obj.defaults["release"]
    if tox is None:
        tox = defaults.get("tox", False)
    if sign_assets is None:
        sign_assets = defaults.get("sign_assets", False)
    if bump is not None:
        if version is not None:
            raise click.UsageError(
                "Explicit version and version bump options are mutually exclusive"
            )
        last_tag = project.repo.get_latest_tag()
        if last_tag is None:
            raise click.UsageError(
                "Cannot use version bump options when there are no tags"
            )
        version = bump_version(last_tag, bump)
    add_type("application/zip", ".whl", False)
    Releaser.from_project(
        project=project,
        version=version,
        gh=obj.gh,
        tox=tox,
        sign_assets=sign_assets,
    ).run()


def get_mime_type(filename: str, strict: bool = False) -> str:
    """
    Like `mimetypes.guess_type()`, except that if the file is compressed, the
    MIME type for the compression is returned.  Also, the default return value
    is now ``"application/octet-stream"`` instead of `None`.
    """
    mtype, encoding = guess_type(filename, strict)
    if encoding is None:
        return mtype or "application/octet-stream"
    elif encoding == "gzip":
        # application/gzip is defined by RFC 6713
        return "application/gzip"
        # There is also a "+gzip" MIME structured syntax suffix defined by RFC
        # 8460; exactly when can that be used?
        # return mtype + '+gzip'
    else:
        return "application/x-" + encoding


def advance_devstatus(cfgpath: Path) -> None:
    setup_cfg = ConfigUpdater(delimiters=("=",))
    setup_cfg.read(str(cfgpath), encoding="utf-8")
    if setup_cfg.has_option("metadata", "classifiers"):
        output = []
        matched = False
        for line in setup_cfg["metadata"]["classifiers"].as_list():
            if re.match(r"^\s*#?\s*Development Status :: [123] ", line):
                continue
            elif (
                re.match(r"^\s*#?\s*Development Status :: [4567] ", line)
                and not matched
            ):
                matched = True
                line = line.replace("#", "", 1)
            output.append(line)
        setup_cfg["metadata"]["classifiers"].set_values(output)
        setup_cfg.update_file()
