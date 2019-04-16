from   operator        import attrgetter
import os
from   pathlib         import Path
from   shutil          import copytree
from   click.testing   import CliRunner
import pytest
from   pyrepo          import inspect_project
from   pyrepo.__main__ import main

DATA_DIR = Path(__file__).with_name('data')

def assert_dirtrees_eq(tree1, tree2):
    assert sorted(map(attrgetter("name"), tree1.iterdir())) \
        == sorted(map(attrgetter("name"), tree2.iterdir()))
    for p1 in tree1.iterdir():
        p2 = tree2 / p1.name
        assert p1.is_dir() == p2.is_dir()
        if p1.is_dir():
            assert_dirtrees_eq(p1, p2)
        else:
            assert p1.read_text() == p2.read_text()

def patched_runcmd(*args, **kwargs):
    if args[:-1] == ('git', 'rm', '-f'):
        os.unlink(args[-1])

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'pyrepo_init').iterdir(),
    ids=attrgetter("name"),
)
def test_pyrepo_init(dirpath, mocker, tmp_path):
    tmp_path /= 'tmp'  # copytree() can't copy to a dir that already exists
    copytree(dirpath / 'before', tmp_path)
    options = (dirpath / 'options.txt').read_text().splitlines()
    mocker.patch(
        'pyrepo.inspect_project.get_commit_years',
        return_value=[2016, 2018, 2019],
    )
    mocker.patch('pyrepo.util.runcmd', new=patched_runcmd)
    r = CliRunner().invoke(
        main,
        ['-C', str(tmp_path), 'init'] + options + ['foobar'],
    )
    assert r.exit_code == 0, r.output
    ### TODO: Assert about how runcmd() was called?
    inspect_project.get_commit_years.assert_called_once_with(Path())
    assert_dirtrees_eq(tmp_path, dirpath / 'after')
