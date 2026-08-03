"""Production-startup regression coverage."""

import subprocess
import sys


def test_application_imports_without_pylette_dependency() -> None:
    script = """
import builtins
import sys

original_import = builtins.__import__

def without_pylette(name, *args, **kwargs):
    if name == 'Pylette' and name not in sys.modules:
        raise ModuleNotFoundError("No module named 'Pylette'")
    return original_import(name, *args, **kwargs)

builtins.__import__ = without_pylette
import beatprints_api.main
"""

    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
