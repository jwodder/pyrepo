import json
from   operator         import attrgetter
from   pathlib          import Path
import pytest
from   pyrepo.changelog import Changelog

DATA_DIR = Path(__file__).with_name('data')

@pytest.mark.parametrize('filepath', [
    p for p in (DATA_DIR / 'changelog').iterdir()
      if p.suffix in ('.md', '.rst')
], ids=attrgetter("name"))
def test_readme(filepath):
    with filepath.open(encoding='utf-8') as fp:
        chlog = Changelog.load(fp)
    assert chlog.for_json() \
        == json.loads(filepath.with_suffix('.json').read_text())
    assert str(chlog) == filepath.read_text(encoding='utf-8')
