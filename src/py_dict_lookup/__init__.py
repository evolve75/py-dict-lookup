"""
py_dict_lookup

Package for the `py-dict-lookup` CLI tool.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("py-dict-lookup")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
