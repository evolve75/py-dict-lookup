"""
py_dict_lookup.__main__

Module entry point for `python -m py_dict_lookup`.

This delegates execution to the same CLI entry point used by the
console script defined in pyproject.toml, ensuring consistent behavior
regardless of how the CLI is invoked.
"""

from py_dict_lookup.cli import app

if __name__ == "__main__":
    app()
