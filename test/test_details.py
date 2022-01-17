import json
from pyrepo.details import ProjectDetails
from test_helpers import DATA_DIR


def test_sort_pyversions() -> None:
    spectfile = next((DATA_DIR / "inspect_project").glob("*/_inspect.json"))
    with spectfile.open(encoding="utf-8") as fp:
        data = json.load(fp)
    data["python_versions"] = ["3.8", "3.9", "3.7", "3.6", "3.10"]
    details = ProjectDetails.parse_obj(data)
    assert details.python_versions == ["3.6", "3.7", "3.8", "3.9", "3.10"]
