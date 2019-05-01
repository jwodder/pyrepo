import sys
import click
from   .util import readcmd, runcmd

@click.command()
@click.option('--repo-name', metavar='NAME')
@click.pass_obj
def mkgithub(obj, repo_name):
    if repo_name is None:
        repo_name = readcmd(sys.executable, 'setup.py', '--name')
    description = readcmd(sys.executable, 'setup.py', '--description')
    repo = obj.gh.user.repos.post(json={
        "name": repo_name,
        "description": description,
    })
    if 'origin' in readcmd('git', 'remote').splitlines():
        runcmd('git', 'remote', 'rm', 'origin')
    runcmd('git', 'remote', 'add', 'origin', repo["ssh_url"])
    runcmd('git', 'push', '-u', 'origin', 'master')
