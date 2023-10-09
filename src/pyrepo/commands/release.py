# TODO:
# - Try to give this some level of idempotence
# - Add options/individual commands for doing each release step separately

# External dependencies:
# - git (including push access to repository)
# - gpg (including a key usable for signing)
# - PyPI credentials for twine
# - GitHub access token

# Notable assumptions made by this code:
# - There is no CHANGELOG file until after the initial release has been made.

from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from functools import partial
import logging
from mimetypes import add_type, guess_type
import os
import os.path
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
from typing import Optional
import click
from in_place import InPlace
from linesep import read_paragraphs
from packaging.version import Version
from uritemplate import expand
from ..clack import ConfigurableCommand
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


@dataclass
class Releaser:
    project: Project
    version: str
    ghrepo: GitHub
    tox: bool
    assets: list[Path] = field(default_factory=list)
    release_upload_url: Optional[str] = None

    @classmethod
    def from_project(
        cls,
        project: Project,
        gh: GitHub,
        version: str,
        tox: bool = False,
    ) -> Releaser:
        return cls(
            project=project,
            version=version.lstrip("v"),
            ghrepo=gh.repos[project.details.github_user][project.details.repo_name],
            tox=tox,
        )

    def run(self, use_next_version: bool = True) -> None:
        self.end_dev()
        if self.tox:
            self.tox_check()
        if not self.project.details.uses_versioningit:
            self.build()
            self.twine_check()
        self.commit_version()
        if self.project.details.uses_versioningit:
            self.build()
            self.twine_check()
        self.project.repo.run("push", "--follow-tags")
        self.mkghrelease()
        self.upload()
        self.project.begin_dev(use_next_version)  # Not idempotent

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
            f"Version {self.version}",
            f"v{self.version}",
            env={**os.environ, "GPG_TTY": os.ttyname(0)},
        )

    def mkghrelease(self) -> None:  ### Not idempotent
        log.info("Creating GitHub release ...")
        subject, body = self.project.repo.read(
            "show",
            "-s",
            "--format=%s%x00%b",
            f"v{self.version}^{{commit}}",
        ).split("\0", 1)
        reldata = self.ghrepo.releases.post(
            json={
                "tag_name": f"v{self.version}",
                "name": subject,
                "body": body.strip(),  ### TODO: Remove line wrapping?
                "draft": False,
            }
        )
        self.release_upload_url = reldata["upload_url"]

    def build(self) -> None:  ### Not idempotent
        log.info("Building artifacts ...")
        self.project.build(clean=True)
        self.assets = list((self.project.directory / "dist").iterdir())

    def upload(self) -> None:
        log.info("Uploading artifacts ...")
        assert self.assets, "Nothing to upload"
        self.upload_pypi()
        self.upload_github()

    def upload_pypi(self) -> None:  # Idempotent
        if self.project.private:
            log.info("Private project; not uploading to PyPI")
        else:
            log.info("Uploading artifacts to PyPI ...")
            runcmd(
                sys.executable,
                "-m",
                "twine",
                "upload",
                "--skip-existing",
                *self.assets,
            )

    def upload_github(self) -> None:  ### Not idempotent
        log.info("Uploading artifacts to GitHub release ...")
        assert (
            self.release_upload_url is not None
        ), "Cannot upload to GitHub before creating release"
        for asset in self.assets:
            url = expand(self.release_upload_url, name=asset.name)
            self.ghrepo[url].post(
                headers={"Content-Type": get_mime_type(asset.name)},
                data=asset.read_bytes(),
            )

    def end_dev(self) -> None:  # Idempotent
        log.info("Finalizing version ...")
        self.project.set_version(self.version)
        # Set release date in CHANGELOGs
        for docs in (False, True):
            chlog = self.project.get_changelog(docs=docs)
            if chlog and chlog.sections:
                if docs:
                    log.info("Updating docs/changelog.rst ...")
                else:
                    log.info("Updating CHANGELOG ...")
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
        if not self.project.private:
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


@click.command(cls=ConfigurableCommand, allow_config=["tox"])
@click.option("--tox/--no-tox", help="Run tox before building")
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
@with_project
@cpe_no_tb
def cli(
    project: Project, version: Optional[str], tox: bool, bump: Optional[Bump]
) -> None:
    """Make a new release of the project"""
    if bump is not None:
        if version is not None:
            raise click.UsageError(
                "Explicit version and version bump options are mutually exclusive"
            )
        last_tag = project.repo.get_latest_tag()
        if last_tag is None:
            ### TODO: Permit this when --date is given
            raise click.UsageError(
                "Cannot use version bump options when there are no tags"
            )
        version = bump_version(last_tag, bump)
    elif version is None:
        if project.details.uses_versioningit:
            raise click.UsageError(
                "Project uses versioningit; explicit version or version bump"
                " option required"
            )
        # Remove prerelease & dev release from __version__
        version = Version(project.details.version).base_version
    add_type("application/zip", ".whl", False)
    Releaser.from_project(project=project, version=version, gh=GitHub(), tox=tox).run(
        use_next_version=bump is not Bump.DATE
    )


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
        return f"application/x-{encoding}"
