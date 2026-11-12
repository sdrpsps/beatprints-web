#!/usr/bin/env python3
"""Validate the user-facing update section in the pull request event."""
import json
import os
import sys

from release_summary import END, LANGUAGES, START, extract_summary

with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
    pr = json.load(event_file)["pull_request"]

if pr["head"]["ref"].startswith("release-please--"):
    body = pr.get("body") or ""
    if body.count(START) != 1 or body.count(END) != 1 or any(
        body.count(f"<!-- release-summary:{lang}:{boundary} -->") != 1
        for lang in LANGUAGES for boundary in ("start", "end")
    ):
        print("Release PR is waiting for localized release notes.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
try:
    extract_summary(pr.get("body"))
except ValueError as exc:
    print(f"Invalid PR update notes: {exc}", file=sys.stderr)
    sys.exit(1)
print("PR update notes are valid in all three languages.")
