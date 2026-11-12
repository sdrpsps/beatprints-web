#!/usr/bin/env python3
"""Add merged PRs' user-facing notes to an existing GitHub release."""

import json
import os
import re
import subprocess
import sys

START = "<!-- release-summary:start -->"
END = "<!-- release-summary:end -->"
LANGUAGES = {"zh-CN": "简体中文", "zh-TW": "繁體中文", "en": "English"}
HEADING = re.compile(r"^##\s+What's New\s*#*\s*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,2}\s+", re.MULTILINE)
LANG_HEADING = re.compile(r"^###\s+(简体中文|繁體中文|English)\s*#*\s*$", re.MULTILINE)
NONE = {lang: "None" for lang in LANGUAGES}
EMPTY_RELEASE = {"zh-CN": "无用户可见更新。", "zh-TW": "無使用者可見更新。", "en": "No user-visible changes."}


def extract_summary(body):
    """Parse a PR's complete localized notes; reject missing or ambiguous sections."""
    match = HEADING.search(body or "")
    if not match:
        raise ValueError("Missing ## What's New")
    remainder = body[match.end():]
    next_heading = NEXT_HEADING.search(remainder)
    section = remainder[:next_heading.start()] if next_heading else remainder
    section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)
    headings = list(LANG_HEADING.finditer(section))
    if len(headings) != 3 or {h.group(1) for h in headings} != set(LANGUAGES.values()):
        raise ValueError("Expected exactly one section for 简体中文, 繁體中文 and English")
    if section[:headings[0].start()].strip():
        raise ValueError("Put update notes under the three language headings")
    values = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        values[heading.group(1)] = section[heading.end():end].strip()
    summaries = {lang: values[label] for lang, label in LANGUAGES.items()}
    for lang, value in summaries.items():
        if value != NONE[lang] and (not value or any(not line.strip().startswith("- ") for line in value.splitlines() if line.strip())):
            raise ValueError(f"{LANGUAGES[lang]} needs Markdown bullets or '{NONE[lang]}'")
    empty = [summaries[lang] == NONE[lang] for lang in LANGUAGES]
    if any(empty) and not all(empty):
        raise ValueError("Use the no-visible-update marker in all three languages")
    return {lang: "" if all(empty) else value for lang, value in summaries.items()}


def update_body(body, summaries):
    # Replace only our own section, so retrying never duplicates release notes.
    original = body or ""
    managed = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"(?:\r?\n){0,2}", re.DOTALL)
    original = managed.sub("", original, count=1)
    blocks = []
    for lang, label in LANGUAGES.items():
        notes = "\n\n".join(item[lang] for item in summaries if item[lang]) or EMPTY_RELEASE[lang]
        blocks.append(f"<!-- release-summary:{lang}:start -->\n## {label}\n\n{notes}\n<!-- release-summary:{lang}:end -->")
    separator = "\n\n---" if original.strip() else ""
    return f"{START}\n" + "\n\n".join(blocks) + separator + f"\n{END}\n\n" + original


def run(*args, input_text=None):
    return subprocess.run(args, input=input_text, text=True, check=True, capture_output=True).stdout.strip()


def gh_json(*args):
    return json.loads(run("gh", "api", *args))


def collect_summaries(repo, default_branch, previous, revision):
    commits = run("git", "rev-list", "--first-parent", "--reverse", f"{previous}..{revision}").splitlines()
    summaries = []
    seen = set()
    for sha in commits:
        pages = gh_json("--paginate", "--slurp", f"repos/{repo}/commits/{sha}/pulls", "-f", "per_page=100", "--method", "GET")
        for pr in (item for page in pages for item in page):
            number = pr["number"]
            if number in seen or not pr.get("merged_at") or pr["base"]["ref"] != default_branch:
                continue
            seen.add(number)
            try:
                summary = extract_summary(pr.get("body"))
            except ValueError as exc:
                print(f"Skipping PR #{number}: {exc}", file=sys.stderr)
                continue
            if any(summary.values()):
                summaries.append(summary)
    return summaries


def main():
    tag = os.environ["RELEASE_TAG"]
    repo = os.environ["GITHUB_REPOSITORY"]
    default_branch = os.environ["DEFAULT_BRANCH"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Expected a stable version tag, such as v1.4.0")
    previous = run("git", "describe", "--first-parent", "--tags", "--abbrev=0", "--match", "v[0-9]*", f"{tag}^")
    summaries = collect_summaries(repo, default_branch, previous, tag)
    release = gh_json(f"repos/{repo}/releases/tags/{tag}")
    body = update_body(release.get("body"), summaries)
    if body != (release.get("body") or ""):
        run("gh", "api", "--method", "PATCH", f"repos/{repo}/releases/{release['id']}", "--input", "-", input_text=json.dumps({"body": body}, ensure_ascii=False))
    print(f"Updated {tag}: {len(summaries)} PR summaries (since {previous}).")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Release summary failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
