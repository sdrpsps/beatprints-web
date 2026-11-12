#!/usr/bin/env python3
"""Validate the user-facing update section in the pull request event."""
import json
import os
import sys

from release_summary import extract_summary

with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
    pr = json.load(event_file)["pull_request"]

# Release Please's generated PR contains the technical changelog, not feature notes.
if pr["head"]["ref"].startswith("release-please--"):
    sys.exit(0)
try:
    extract_summary(pr.get("body"))
except ValueError as exc:
    print(f"Invalid PR update notes: {exc}", file=sys.stderr)
    sys.exit(1)
print("PR update notes are valid in all three languages.")
