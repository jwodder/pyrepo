import click
from ..gh import ACCEPT
from ..inspecting import InvalidProjectError, inspect_project
from ..util import readcmd, runcmd

TOPICS_ACCEPT = f"application/vnd.github.mercy-preview,{ACCEPT}"


@click.command()
@click.option("-P", "--private", is_flag=True, help="Make the new repo private")
@click.option("--repo-name", metavar="NAME", help="Set the name of the repository")
@click.pass_obj
def cli(obj, repo_name, private):
    """Create a repository on GitHub for the local project and upload it"""
    try:
        env = inspect_project()
    except InvalidProjectError as e:
        raise click.UsageError(str(e))
    if repo_name is None:
        repo_name = env["repo_name"]
    repo = obj.gh.user.repos.post(
        json={
            "name": repo_name,
            "description": env["short_description"],
            "private": private,
        }
    )
    keywords = [kw.lower().replace(" ", "-") for kw in env["keywords"]]
    if "python" not in keywords:
        keywords.append("python")
    obj.gh[repo["url"]].topics.put(
        headers={"Accept": TOPICS_ACCEPT},
        json={"names": keywords},
    )
    if "origin" in readcmd("git", "remote").splitlines():
        runcmd("git", "remote", "rm", "origin")
    runcmd("git", "remote", "add", "origin", repo["ssh_url"])
    runcmd("git", "push", "-u", "origin", env["default_branch"])
