import json
from   operator          import attrgetter
from   pathlib           import Path
from   shutil            import copyfile
import time
import pytest
from   pyrepo            import util
from   pyrepo.inspecting import (
    InvalidProjectError, extract_requires, find_module, get_commit_years,
    inspect_project, parse_requirements,
)
from   pyrepo.project    import Project

DATA_DIR = Path(__file__).with_name('data')

@pytest.mark.parametrize('gitoutput,result', [
    ('2019\n2019\n2018\n2016', [2016, 2018, 2019]),
    ('2018\n2016', [2016, 2018, 2019]),
    ('2019', [2019]),
    ('', [2019]),
    ('2018', [2018, 2019]),
])
def test_get_commit_years_include_now(gitoutput, result, mocker):
    # Set current time to 2019-04-16T18:17:14Z:
    mocker.patch('time.localtime', return_value=time.localtime(1555438634))
    mocker.patch('pyrepo.util.readcmd', return_value=gitoutput)
    assert get_commit_years(Path()) == result
    util.readcmd.assert_called_once_with(
        'git', 'log', '--format=%ad', '--date=format:%Y', cwd=Path()
    )
    time.localtime.assert_called_once_with()

@pytest.mark.parametrize('gitoutput,result', [
    ('2019\n2019\n2018\n2016', [2016, 2018, 2019]),
    ('2018\n2016', [2016, 2018]),
    ('2019', [2019]),
    ('', []),
    ('2018', [2018]),
])
def test_get_commit_years_no_include_now(gitoutput, result, mocker):
    # Set current time to 2019-04-16T18:17:14Z:
    mocker.patch('time.localtime', return_value=time.localtime(1555438634))
    mocker.patch('pyrepo.util.readcmd', return_value=gitoutput)
    assert get_commit_years(Path(), include_now=False) == result
    util.readcmd.assert_called_once_with(
        'git', 'log', '--format=%ad', '--date=format:%Y', cwd=Path()
    )
    time.localtime.assert_not_called()

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'find_module' / 'valid').iterdir()),
    ids=attrgetter("name"),
)
def test_find_module(dirpath):
    assert find_module(dirpath) == {
        "import_name": "foobar",
        "is_flat_module": dirpath.name.endswith("flat"),
        "src_layout": False,
    }

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'find_module' / 'valid-src').iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_src(dirpath):
    assert find_module(dirpath) == {
        "import_name": "foobar",
        "is_flat_module": dirpath.name.endswith("flat"),
        "src_layout": True,
    }

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'find_module' / 'extra').iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_extra(dirpath):
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == 'Multiple Python modules in repository'

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'find_module' / 'none').iterdir()),
    ids=attrgetter("name"),
)
def test_find_module_none(dirpath):
    with pytest.raises(InvalidProjectError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == 'No Python modules in repository'

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'extract_requires').iterdir()),
    ids=attrgetter("name"),
)
def test_extract_requires(dirpath, tmp_path):
    dest = tmp_path / 'foobar.py'
    copyfile(dirpath / 'before.py', dest)
    variables = extract_requires(dest)
    with (dirpath / 'variables.json').open() as fp:
        assert variables == json.load(fp)
    assert (dirpath / 'after.py').read_text() == dest.read_text()

@pytest.mark.parametrize(
    'reqfile',
    sorted((DATA_DIR / 'parse_requirements').glob("*.txt")),
    ids=attrgetter("name"),
)
def test_parse_requirements(reqfile):
    variables = parse_requirements(reqfile)
    assert variables == json.loads(reqfile.with_suffix('.json').read_text())

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'inspect_project').iterdir()),
    ids=attrgetter("name"),
)
def test_inspect_project(dirpath):
    if (dirpath / '_errmsg.txt').exists():
        with pytest.raises(Exception) as excinfo:
            inspect_project(dirpath)
        assert str(excinfo.value) \
            == (dirpath / '_errmsg.txt').read_text().strip()
    else:
        env = inspect_project(dirpath)
        assert env == json.loads((dirpath / '_inspect.json').read_text())
        project = Project.from_inspection(dirpath, env)
        assert project.get_template_context() == env
