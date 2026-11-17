"""Production-startup regression coverage."""

import ast
import subprocess
import sys


def test_catalog_capabilities_follow_the_provider_registry_order() -> None:
    from fastapi.testclient import TestClient
    from beatprints_api.main import app

    response = TestClient(app).get("/v1/capabilities")
    assert response.status_code == 200
    assert [item["key"] for item in response.json()["data"]["catalogs"]] == [
        "apple_music",
        "spotify",
        "qq_music",
        "netease_music",
    ]


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


def test_each_integration_can_be_disabled_by_its_registry_import(tmp_path) -> None:
    """A fresh application must not indirectly re-register a removed plugin."""
    import json
    import shutil
    from pathlib import Path

    import beatprints_api

    source = Path(beatprints_api.__file__).parent
    registry_modules = {
        "catalog": ("qq_music", "netease_music", "spotify", "apple_music"),
        "destinations": ("spotify", "apple_music", "qq_music", "netease_music"),
        "lyrics": ("qq_music", "netease", "lrclib"),
    }
    roles = {"catalog": "catalogs", "destinations": "destinations", "lyrics": "lyrics"}
    for kind, modules in registry_modules.items():
        for module in modules:
            target = tmp_path / f"{kind}_{module}"
            shutil.copytree(
                source,
                target / "beatprints_api",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            registry = target / "beatprints_api" / "integrations" / kind / "registry.py"
            lines = registry.read_text().splitlines(keepends=True)
            imports = ast.parse("".join(lines)).body
            matches = [
                node
                for node in imports
                if isinstance(node, ast.ImportFrom)
                and node.module == f"beatprints_api.integrations.{kind}"
                and len(node.names) == 1
                and node.names[0].name == module
            ]
            assert len(matches) == 1
            registry.write_text(
                "".join(lines[: matches[0].lineno - 1] + lines[matches[0].end_lineno :])
            )
            script = """
import json
from fastapi.testclient import TestClient
from beatprints_api.main import app
response = TestClient(app).get('/v1/capabilities')
assert response.status_code == 200
print(json.dumps(response.json()['data']))
"""
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=target,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stderr
            data = json.loads(result.stdout.splitlines()[-1])
            assert module not in {item["key"] for item in data[roles[kind]]}
            if module in (
                "spotify",
                "apple_music",
                "qq_music",
                "netease_music",
            ) and kind in ("catalog", "destinations"):
                other = "destinations" if kind == "catalog" else "catalogs"
                assert module in {item["key"] for item in data[other]}
