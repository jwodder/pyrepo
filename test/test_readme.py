import json
from operator import attrgetter
from pathlib import Path
import pytest
from pyrepo.readme import Readme
from test_helpers import DATA_DIR


@pytest.mark.parametrize(
    "filepath",
    (DATA_DIR / "readme").glob("*.rst"),
    ids=attrgetter("name"),
)
def test_readme(filepath: Path) -> None:
    with filepath.open(encoding="utf-8") as fp:
        rme = Readme.load(fp)
    assert rme.for_json() == json.loads(filepath.with_suffix(".json").read_text())
    assert str(rme) == filepath.read_text(encoding="utf-8")
