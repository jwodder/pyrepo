from base64 import b64encode
import logging
import re
import click
from nacl import encoding, public
from ..clack import ConfigurableCommand
from ..gh import GitHub
from ..project import Project, with_project
from ..util import cpe_no_tb

log = logging.getLogger(__name__)


@click.command(cls=ConfigurableCommand, allow_config=["codecov_token"])
@click.option(
    "--codecov-token",
    help="Value for CODECOV_TOKEN actions secret",
    metavar="SECRET",
    envvar="CODECOV_TOKEN",
    show_envvar=True,
)
@click.option(
    "--no-codecov-token", is_flag=True, help="Do not set CODECOV_TOKEN actions secret"
)
@click.option("-P", "--private", is_flag=True, help="Make the new repo private")
@click.option("--repo-name", metavar="NAME", help="Set the name of the repository")
@with_project
@cpe_no_tb
def cli(
    project: Project,
    repo_name: str | None,
    private: bool,
    codecov_token: str | None,
    no_codecov_token: bool,
) -> None:
    """Create a repository on GitHub for the local project and upload it"""
    if repo_name is None:
        repo_name = project.details.repo_name
    log.info("Creating GitHub repository %r", repo_name)
    with GitHub() as gh:
        r = gh.post(
            "/user/repos",
            {
                "name": repo_name,
                "description": project.details.short_description,
                "private": private,
                "delete_branch_on_merge": True,
            },
        )
        ghrepo = gh / r["url"]
        keywords = [
            re.sub(r"[^a-z0-9]+", "-", kw.lower()) for kw in project.details.keywords
        ]
        if "python" not in keywords:
            keywords.append("python")
        log.info("Setting repository topics to: %s", " ".join(keywords))
        (ghrepo / "topics").put({"names": keywords})
        if (project.directory / ".github" / "dependabot.yml").exists():
            log.info('Creating "dependencies" label')
            (ghrepo / "labels").post(
                {
                    "name": "dependencies",
                    "color": "8732bc",
                    "description": "Update one or more dependencies' versions",
                }
            )
            log.info('Creating "d:github-actions" label')
            (ghrepo / "labels").post(
                {
                    "name": "d:github-actions",
                    "color": "74fa75",
                    "description": "Update a GitHub Actions action dependency",
                }
            )
            log.info('Creating "d:python" label')
            (ghrepo / "labels").post(
                {
                    "name": "d:python",
                    "color": "3572a5",
                    "description": "Update a Python dependency",
                }
            )
            if not no_codecov_token:
                if codecov_token:
                    for scope in ["actions", "dependabot"]:
                        log.info("Setting CODECOV_TOKEN secret (%s)", scope)
                        secrets = ghrepo / scope / "secrets"
                        pubkey = (secrets / "public-key").get()
                        (secrets / "CODECOV_TOKEN").put(
                            {
                                "encrypted_value": encrypt_secret(
                                    pubkey["key"], codecov_token
                                ),
                                "key_id": pubkey["key_id"],
                            }
                        )
                else:
                    log.warn("CODECOV_TOKEN value not set; not setting secret")
    log.info('Setting "origin" remote')
    if "origin" in project.repo.get_remotes():
        project.repo.rm_remote("origin")
    project.repo.add_remote("origin", r["ssh_url"])
    log.info("Pushing to origin")
    project.repo.run("push", "-u", "origin", "refs/heads/*", "refs/tags/*")


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Encrypt a string for use as a GitHub secret using a public key"""
    pkey = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(pkey)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")
