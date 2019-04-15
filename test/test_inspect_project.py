from   operator               import attrgetter
from   pathlib                import Path
import pytest
from   pyrepo.inspect_project import is_flat

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
