from typing import Optional
import click
from ..config import Config
from ..project import Project, with_project
from ..util import cpe_no_tb


@click.command()
@click.option("-P", "--private", is_flag=True, help="Make the new repo private")
@click.option("--repo-name", metavar="NAME", help="Set the name of the repository")
@click.pass_obj
@with_project
@cpe_no_tb
def cli(obj: Config, project: Project, repo_name: Optional[str], private: bool) -> None:
    """Create a repository on GitHub for the local project and upload it"""
    if repo_name is None:
        repo_name = project.details.repo_name
    r = obj.gh.user.repos.post(
        json={
            "name": repo_name,
            "description": project.details.short_description,
            "private": private,
            "delete_branch_on_merge": True,
        }
    )
    keywords = [kw.lower().replace(" ", "-") for kw in project.details.keywords]
    if "python" not in keywords:
        keywords.append("python")
    obj.gh[r["url"]].topics.put(json={"names": keywords})
    if "origin" in project.repo.get_remotes():
        project.repo.rm_remote("origin")
    project.repo.add_remote("origin", r["ssh_url"])
    project.repo.run("push", "-u", "origin", "refs/heads/*", "refs/tags/*")
