import json
from   operator               import attrgetter
from   pathlib                import Path
from   shutil                 import copyfile
import time
import pytest
from   pyrepo                 import util
from   pyrepo.inspect_project import extract_requires, find_module, \
                                        get_commit_years, is_flat, \
                                        parse_requirements

DATA_DIR = Path(__file__).with_name('data')

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'is_flat' / 'flat').iterdir(),
    ids=attrgetter("name"),
)
def test_is_flat_yes(dirpath):
    assert is_flat(dirpath, "foobar")

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'is_flat' / 'notflat').iterdir(),
    ids=attrgetter("name"),
)
def test_is_flat_no(dirpath):
    assert not is_flat(dirpath, "foobar")

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'is_flat' / 'both').iterdir(),
    ids=attrgetter("name"),
)
def test_is_flat_both(dirpath):
    with pytest.raises(ValueError) as excinfo:
        is_flat(dirpath, "foobar")
    assert str(excinfo.value) \
        == 'Both foobar.py and foobar/__init__.py present in repository'

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'is_flat' / 'neither').iterdir(),
    ids=attrgetter("name"),
)
def test_is_flat_neither(dirpath):
    with pytest.raises(ValueError) as excinfo:
        is_flat(dirpath, "foobar")
    assert str(excinfo.value) \
        == 'Neither foobar.py nor foobar/__init__.py present in repository'

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
        'git', '-C', '.', 'log', '--format=%ad', '--date=format:%Y',
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
        'git', '-C', '.', 'log', '--format=%ad', '--date=format:%Y',
    )
    time.localtime.assert_not_called()

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'find_module' / 'valid').iterdir(),
    ids=attrgetter("name"),
)
def test_find_module(dirpath):
    assert find_module(dirpath) == {
        "import_name": "foobar",
        "is_flat_module": dirpath.name.endswith("flat"),
    }

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'find_module' / 'extra').iterdir(),
    ids=attrgetter("name"),
)
def test_find_module_extra(dirpath):
    with pytest.raises(ValueError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == 'Multiple Python modules in repository'

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'find_module' / 'none').iterdir(),
    ids=attrgetter("name"),
)
def test_find_module_none(dirpath):
    with pytest.raises(ValueError) as excinfo:
        find_module(dirpath)
    assert str(excinfo.value) == 'No Python modules in repository'

@pytest.mark.parametrize(
    'dirpath',
    (DATA_DIR / 'extract_requires').iterdir(),
    ids=attrgetter("name"),
)
def test_extract_requires(dirpath, tmp_path):
    dest = tmp_path / 'foobar.py'
    copyfile(dirpath / 'before.py', dest)
    variables = extract_requires(dest)
    with (dirpath / 'variables.json').open() as fp:
        assert variables == json.load(fp)
    assert (dirpath / 'after.py').read_text() == dest.read_text()

@pytest.mark.parametrize('reqfile', [
    p for p in (DATA_DIR / 'parse_requirements').iterdir()
      if p.suffix == '.txt'
], ids=attrgetter("name"))
def test_parse_requirements(reqfile):
    variables = parse_requirements(reqfile)
    assert variables == json.loads(reqfile.with_suffix('.json').read_text())
