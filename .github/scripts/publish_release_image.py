#!/usr/bin/env python3
"""Publish a verified release image before making its GitHub release public."""

import json
import os
import re
import subprocess
import sys
import time

STABLE_TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PRERELEASE_TAG = re.compile(
    r"^v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)-[0-9A-Za-z][0-9A-Za-z.-]*$"
)
SHA = re.compile(r"^[0-9a-f]{40,64}$")


def run(*args, input_text=None):
    return subprocess.run(
        args, input=input_text, text=True, check=True, capture_output=True
    ).stdout.strip()


def releases(repo):
    pages = json.loads(
        run(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/releases",
            "--method",
            "GET",
            "-f",
            "per_page=100",
        )
    )
    return [release for page in pages for release in page]


def find_release(repo, tag, attempts=13, interval=5):
    # Release Please creates the tag immediately before the draft; a fast image
    # build must wait for that draft instead of publishing a tag by itself.
    for attempt in range(attempts):
        known = releases(repo)
        matching = [release for release in known if release.get("tag_name") == tag]
        if len(matching) == 1:
            return matching[0], known
        if len(matching) > 1:
            raise ValueError(f"Multiple releases use {tag}")
        if attempt + 1 < attempts:
            time.sleep(interval)
    raise ValueError(f"No GitHub release or draft exists for {tag}")


def version_tuple(tag):
    match = STABLE_TAG.fullmatch(tag)
    return tuple(int(part) for part in match.groups()) if match else None


def floating_tags(tag, release, known):
    """Only the newest published stable version may advance each moving tag."""
    version = version_tuple(tag)
    if version is None or release.get("prerelease"):
        return []
    published = [
        parsed
        for item in known
        if not item.get("draft") and not item.get("prerelease")
        if (parsed := version_tuple(item.get("tag_name", ""))) is not None
    ]
    major, minor, _patch = version
    tags = []
    if not any(item[:2] == version[:2] and item > version for item in published):
        tags.append(f"{major}.{minor}")
    if not any(item[0] == major and item > version for item in published):
        tags.append(str(major))
    if not any(item > version for item in published):
        tags.append("latest")
    return tags


def verify_platforms(raw):
    manifest = json.loads(raw)
    platforms = {
        (
            entry.get("platform", {}).get("os"),
            entry.get("platform", {}).get("architecture"),
        )
        for entry in manifest.get("manifests", [])
    }
    required = {("linux", "amd64"), ("linux", "arm64")}
    if not required <= platforms:
        raise ValueError(
            f"Published manifest is missing required architectures: {sorted(required - platforms)}"
        )


def verify_image_identity(image, platform, tag, sha):
    config = image.get("config", {})
    labels = config.get("Labels") or {}
    env = set(config.get("Env") or [])
    if (
        image.get("os") != "linux"
        or image.get("architecture") != platform
        or labels.get("org.opencontainers.image.version") != tag
        or labels.get("org.opencontainers.image.revision") != sha
        or f"BEATPRINTS_VERSION={tag}" not in env
        or f"BEATPRINTS_GIT_SHA={sha}" not in env
    ):
        raise ValueError(
            f"linux/{platform} image version or revision does not match {tag} at {sha}"
        )


def publish(repo, image, tag, sha):
    if not (STABLE_TAG.fullmatch(tag) or PRERELEASE_TAG.fullmatch(tag)):
        raise ValueError("Expected a version tag such as v1.5.0 or v1.5.0-rc.1")
    if not SHA.fullmatch(sha):
        raise ValueError("Expected the full release commit SHA")
    release, known = find_release(repo, tag)
    if not STABLE_TAG.fullmatch(tag) and not release.get("prerelease"):
        raise ValueError("A prerelease tag must have a GitHub prerelease")
    version_tag = f"{image}:{tag[1:]}"
    sha_tag = f"{image}:sha-{sha[:7]}"
    for architecture in ("amd64", "arm64"):
        source = f"{image}:build-{sha}-{architecture}"
        config = json.loads(
            run(
                "docker",
                "buildx",
                "imagetools",
                "inspect",
                source,
                "--format",
                "{{json .Image}}",
            )
        )
        verify_image_identity(config, architecture, tag, sha)
    run(
        "docker",
        "buildx",
        "imagetools",
        "create",
        "--tag",
        version_tag,
        "--tag",
        sha_tag,
        f"{image}:build-{sha}-amd64",
        f"{image}:build-{sha}-arm64",
    )
    verify_platforms(
        run("docker", "buildx", "imagetools", "inspect", "--raw", version_tag)
    )
    images = json.loads(
        run(
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            version_tag,
            "--format",
            "{{json .Image}}",
        )
    )
    for architecture in ("amd64", "arm64"):
        verify_image_identity(
            images.get(f"linux/{architecture}", {}), architecture, tag, sha
        )
    aliases = floating_tags(tag, release, known)
    if aliases:
        tags = [
            argument for alias in aliases for argument in ("--tag", f"{image}:{alias}")
        ]
        run("docker", "buildx", "imagetools", "create", *tags, version_tag)
    if release.get("draft"):
        payload = json.dumps(
            {"draft": False, "make_latest": "true" if "latest" in aliases else "false"}
        )
        run(
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{repo}/releases/{release['id']}",
            "--input",
            "-",
            input_text=payload,
        )
    print(
        f"Published verified {tag} image; floating tags: {', '.join(aliases) or 'none'}."
    )


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    image = f"{os.environ['REGISTRY']}/{os.environ['IMAGE_NAME'].lower()}"
    publish(repo, image, os.environ["RELEASE_TAG"], os.environ["RELEASE_SHA"])


if __name__ == "__main__":
    try:
        main()
    except (
        KeyError,
        ValueError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Release image publication failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr, file=sys.stderr)
        sys.exit(1)
