"""
Python repository packager & releaser

``jwodder-pyrepo`` is my personal project for managing my Python package
repositories, including generating packaging boilerplate and performing
releases.  It is heavily dependent upon the conventions I use in building &
structuring Python projects, and so it is not suitable for general use.

Visit <https://github.com/jwodder/pyrepo> for more information.
"""

from importlib.metadata import version

__version__ = version("jwodder-pyrepo")
__author__ = "John Thorvald Wodder II"
__author_email__ = "pyrepo@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/pyrepo"
