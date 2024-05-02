import logging
import re
import click
from ..gh import GitHub
from ..project import Project, with_project
from ..util import cpe_no_tb

log = logging.getLogger(__name__)


@click.command()
@click.option("-P", "--private", is_flag=True, help="Make the new repo private")
@click.option("--repo-name", metavar="NAME", help="Set the name of the repository")
@with_project
@cpe_no_tb
def cli(project: Project, repo_name: str | None, private: bool) -> None:
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
    log.info('Setting "origin" remote')
    if "origin" in project.repo.get_remotes():
        project.repo.rm_remote("origin")
    project.repo.add_remote("origin", r["ssh_url"])
    log.info("Pushing to origin")
    project.repo.run("push", "-u", "origin", "refs/heads/*", "refs/tags/*")
