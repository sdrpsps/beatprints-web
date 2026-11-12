#!/usr/bin/env python3
"""Add localized notes to the release PR before Release Please creates a release."""

import json
import os
import re
import subprocess
import sys

from release_summary import collect_summaries, gh_json, run, update_body


def prepare_body(body, summaries):
    # Release Please parses the first and last standalone --- as PR delimiters,
    # and requires the release notes to start with the version heading.
    delimiters = list(re.finditer(r"(?m)^---[ \t]*$", body))
    if len(delimiters) < 2:
        raise ValueError("Release PR is missing its expected delimiters")
    start, end = delimiters[0].end(), delimiters[-1].start()
    content = body[start:end]
    heading = re.match(r"(\s*##\s+\[?\d+\.\d+\.\d+[^\n]*\n)(.*)", content, re.DOTALL)
    if not heading:
        raise ValueError("Release PR is missing its expected version heading")
    notes = update_body(heading.group(2).strip(), summaries)
    return body[:start] + heading.group(1) + "\n" + notes + "\n\n" + body[end:]


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["DEFAULT_BRANCH"]
    prs = gh_json("--paginate", "--slurp", f"repos/{repo}/pulls", "-f", "state=open", "-f", f"base={branch}", "-f", "per_page=100", "--method", "GET")
    prs = [pr for page in prs for pr in page if pr["head"]["ref"].startswith("release-please--")]
    if not prs:
        print("No open Release Please PR to update.")
        return
    if len(prs) != 1:
        raise ValueError("Expected exactly one open Release Please PR")
    previous = run("git", "describe", "--first-parent", "--tags", "--abbrev=0", "--match", "v[0-9]*", "HEAD")
    summaries = collect_summaries(repo, branch, previous, "HEAD")
    pr = prs[0]
    body = prepare_body(pr["body"] or "", summaries)
    if body != pr["body"]:
        run("gh", "api", "--method", "PATCH", f"repos/{repo}/pulls/{pr['number']}", "--input", "-", input_text=json.dumps({"body": body}, ensure_ascii=False))
    print(f"Prepared PR #{pr['number']} with {len(summaries)} summaries since {previous}.")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Release PR preparation failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
