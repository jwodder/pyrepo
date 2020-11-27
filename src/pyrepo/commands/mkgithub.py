import click
from   ..gh         import ACCEPT
from   ..inspecting import UninitializedProjectError, inspect_project
from   ..util       import readcmd, runcmd

TOPICS_ACCEPT = f'application/vnd.github.mercy-preview,{ACCEPT}'

@click.command()
@click.option('-P', '--private', is_flag=True)
@click.option('--repo-name', metavar='NAME')
@click.pass_obj
def cli(obj, repo_name, private):
    try:
        env = inspect_project()
    except UninitializedProjectError as e:
        raise click.UsageError(str(e))
    if repo_name is None:
        repo_name = env["repo_name"]
    repo = obj.gh.user.repos.post(json={
        "name": repo_name,
        "description": env["short_description"],
        "private": private,
    })
    keywords = [kw.replace(' ', '-') for kw in env["keywords"]]
    if "python" not in keywords:
        keywords.append("python")
    obj.gh[repo["url"]].topics.put(
        headers={"Accept": TOPICS_ACCEPT},
        json={"names": keywords},
    )
    if 'origin' in readcmd('git', 'remote').splitlines():
        runcmd('git', 'remote', 'rm', 'origin')
    runcmd('git', 'remote', 'add', 'origin', repo["ssh_url"])
    runcmd('git', 'push', '-u', 'origin', 'master')
