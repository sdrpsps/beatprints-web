#!/usr/bin/env python3
"""Decide whether a release PR changes only version metadata and changelog."""

import json
import os
import re
import subprocess
import tomllib

ALLOWED_FILES = {"CHANGELOG.md", "VERSION", ".release-please-manifest.json", "pyproject.toml", "uv.lock"}


def normalize(path, content):
    if path == "CHANGELOG.md":
        return None
    if path == "VERSION":
        if not re.fullmatch(r"\d+\.\d+\.\d+", content.strip()):
            raise ValueError("Expected a stable version")
        return None
    if path == ".release-please-manifest.json":
        data = json.loads(content)
        del data["."]
        return data
    if path == "pyproject.toml":
        data = tomllib.loads(content)
        del data["project"]["version"]
        return data
    if path == "uv.lock":
        data = tomllib.loads(content)
        packages = [package for package in data["package"] if package.get("name") == "beatprints-api"]
        if len(packages) != 1:
            raise ValueError("Expected one beatprints-api package")
        del packages[0]["version"]
        return data
    raise ValueError(f"Unexpected file: {path}")


def version_only(changes):
    if not changes:
        return False
    try:
        return all(normalize(path, before) == normalize(path, after) for path, before, after in changes)
    except (KeyError, TypeError, ValueError):
        return False


def git(*args):
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout


def main():
    base, head = os.environ["BASE_SHA"], os.environ["HEAD_SHA"]
    paths = git("diff", "--name-only", "--no-renames", "-z", base, head).split("\0")
    paths = [path for path in paths if path]
    try:
        if not set(paths) <= ALLOWED_FILES:
            result = False
        else:
            changes = [(path, git("show", f"{base}:{path}"), git("show", f"{head}:{path}")) for path in paths]
            result = version_only(changes)
    except (subprocess.CalledProcessError, UnicodeError):
        # Missing or deleted files should cause a build, not skip validation.
        result = False
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        print(f"version-only={str(result).lower()}", file=output)
    print("Version-only release PR:", result)


if __name__ == "__main__":
    main()
