import json
from   operator      import attrgetter
from   pathlib       import Path
import pytest
from   pyrepo.readme import Readme

DATA_DIR = Path(__file__).with_name('data')

@pytest.mark.parametrize('filepath', [
    p for p in (DATA_DIR / 'readme').iterdir()
      if p.suffix == '.rst'
], ids=attrgetter("name"))
def test_readme(filepath):
    with filepath.open(encoding='utf-8') as fp:
        rme = Readme.parse(fp)
    assert rme.for_json() \
        == json.loads(filepath.with_suffix('.json').read_text())
    assert str(rme) == filepath.read_text(encoding='utf-8')
