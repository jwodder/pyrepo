from __future__ import annotations
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel, validator
from .inspecting import inspect_project
from .tmpltr import Templater
from .util import PyVersion


class ProjectDetails(BaseModel):
    #: The name of the project as it is/will be known on PyPI
    name: str

    version: str
    short_description: str
    author: str
    author_email: str
    install_requires: List[str]
    keywords: List[str]
    classifiers: List[str]
    supports_pypy: bool

    #: Extra testenvs to include runs for in CI, as a mapping from testenv name
    #: to Python version
    extra_testenvs: Dict[str, str]

    is_flat_module: bool
    import_name: str
    uses_versioningit: bool

    #: Sorted list of supported Python versions
    python_versions: List[PyVersion]

    python_requires: str

    #: Mapping from command (`console_scripts`) names to entry point
    #: specifications
    commands: Dict[str, str]

    github_user: str
    codecov_user: str
    repo_name: str
    rtfd_name: str
    has_tests: bool
    has_typing: bool
    has_doctests: bool
    has_docs: bool
    has_ci: bool
    has_pypi: bool
    copyright_years: List[int]
    default_branch: str

    @validator("python_versions")
    @classmethod
    def _sort_python_versions(cls, v: list[PyVersion]) -> list[PyVersion]:
        return sorted(v)

    @classmethod
    def inspect(cls, dirpath: str | Path | None = None) -> ProjectDetails:
        return cls.parse_obj(inspect_project(dirpath))

    def get_templater(self) -> Templater:
        return Templater(context=self.dict())
