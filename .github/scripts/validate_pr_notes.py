#!/usr/bin/env python3
"""Validate the user-facing update section in the pull request event."""
import json
import os
import sys
import time

from release_summary import END, LANGUAGES, START, extract_summary, gh_json


def has_release_summary(body):
    body = body or ""
    return body.count(START) == 1 and body.count(END) == 1 and all(
        body.count(f"<!-- release-summary:{lang}:{boundary} -->") == 1
        for lang in LANGUAGES for boundary in ("start", "end")
    )


def wait_for_release_summary(pr, repo, attempts=13, interval=5):
    if has_release_summary(pr.get("body")):
        return True
    for _ in range(attempts - 1):
        time.sleep(interval)
        current = gh_json(f"repos/{repo}/pulls/{pr['number']}")
        if has_release_summary(current.get("body")):
            return True
    return False


def main():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event_file:
        pr = json.load(event_file)["pull_request"]
    if pr["head"]["ref"].startswith("release-please--"):
        if wait_for_release_summary(pr, os.environ["GITHUB_REPOSITORY"]):
            print("Release PR contains localized notes.")
            return 0
        print("Release PR is missing localized notes after waiting for the release workflow.", file=sys.stderr)
        return 1
    try:
        extract_summary(pr.get("body"))
    except ValueError as exc:
        print(f"Invalid PR update notes: {exc}", file=sys.stderr)
        return 1
    print("PR update notes are valid in all three languages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
