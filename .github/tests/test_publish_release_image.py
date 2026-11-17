import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "publish_release_image",
    Path(__file__).parents[1] / "scripts" / "publish_release_image.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SHA = "a" * 40
IMAGE = "ghcr.io/owner/beatprints"
MANIFEST = json.dumps(
    {
        "manifests": [
            {"platform": {"os": "linux", "architecture": "amd64"}},
            {"platform": {"os": "linux", "architecture": "arm64"}},
            {"platform": {"os": "unknown", "architecture": "unknown"}},
        ]
    }
)


def image_config(tag):
    return json.dumps(
        {
            platform: {
                "os": "linux",
                "architecture": platform.split("/")[1],
                "config": {
                    "Labels": {
                        "org.opencontainers.image.version": tag,
                        "org.opencontainers.image.revision": SHA,
                    },
                    "Env": [f"BEATPRINTS_VERSION={tag}", f"BEATPRINTS_GIT_SHA={SHA}"],
                },
            }
            for platform in ("linux/amd64", "linux/arm64")
        }
    )


def inspect_result(args, tag):
    if "--raw" in args:
        return MANIFEST
    if "--format" in args:
        images = json.loads(image_config(tag))
        target = args[4]
        if target.endswith("-amd64") or target.endswith("-arm64"):
            return json.dumps(images[f"linux/{target.rsplit('-', 1)[-1]}"])
        return json.dumps(images)
    return ""


def release(tag, *, draft=False, prerelease=False):
    return {"id": 42, "tag_name": tag, "draft": draft, "prerelease": prerelease}


class PublishReleaseImageTests(unittest.TestCase):
    def test_latest_stable_updates_all_aliases(self):
        current = release("v1.5.0", draft=True)
        self.assertEqual(
            module.floating_tags("v1.5.0", current, [release("v1.4.1"), current]),
            ["1.5", "1", "latest"],
        )

    def test_old_release_does_not_roll_back_newer_aliases(self):
        older = release("v1.4.1")
        self.assertEqual(
            module.floating_tags(
                "v1.4.1", older, [older, release("v1.4.2"), release("v1.5.0")]
            ),
            [],
        )
        self.assertEqual(
            module.floating_tags("v1.4.2", older, [older, release("v1.5.0")]), ["1.4"]
        )
        self.assertEqual(
            module.floating_tags(
                "v1.5.0-rc.1", release("v1.5.0-rc.1", prerelease=True), []
            ),
            [],
        )

    def test_draft_is_published_only_after_both_architectures_and_aliases(self):
        current = release("v1.5.0", draft=True)
        calls = []

        def run(*args, input_text=None):
            calls.append((args, input_text))
            return inspect_result(args, "v1.5.0")

        with (
            patch.object(
                module,
                "find_release",
                return_value=(current, [release("v1.4.1"), current]),
            ),
            patch.object(module, "run", side_effect=run),
        ):
            module.publish("owner/repo", IMAGE, "v1.5.0", SHA)
        self.assertEqual(len(calls), 7)
        self.assertIn(f"{IMAGE}:build-{SHA}-amd64", calls[0][0])
        self.assertIn(f"{IMAGE}:build-{SHA}-arm64", calls[1][0])
        self.assertIn("create", calls[2][0])
        self.assertIn("--raw", calls[3][0])
        self.assertIn("--format", calls[4][0])
        self.assertIn(f"{IMAGE}:latest", calls[5][0])
        self.assertEqual(
            json.loads(calls[6][1]), {"draft": False, "make_latest": "true"}
        )

    def test_bad_image_or_alias_failure_leaves_release_draft(self):
        current = release("v1.5.0", draft=True)
        for failure in ("missing", "identity", "alias"):
            calls = []

            def run(*args, input_text=None):
                calls.append(args)
                if "--raw" in args and failure == "missing":
                    return '{"manifests": []}'
                if failure == "alias" and f"{IMAGE}:latest" in args:
                    raise subprocess.CalledProcessError(1, args)
                return inspect_result(
                    args, "v1.4.1" if failure == "identity" else "v1.5.0"
                )

            with (
                self.subTest(failure=failure),
                patch.object(module, "find_release", return_value=(current, [current])),
                patch.object(module, "run", side_effect=run),
                self.assertRaises((ValueError, subprocess.CalledProcessError)),
            ):
                module.publish("owner/repo", IMAGE, "v1.5.0", SHA)
            self.assertFalse(any(args[:2] == ("gh", "api") for args in calls))

    def test_existing_older_release_only_updates_eligible_aliases(self):
        old = release("v1.4.2")
        calls = []

        def run(*args, input_text=None):
            calls.append(args)
            return inspect_result(args, "v1.4.2")

        with (
            patch.object(
                module, "find_release", return_value=(old, [old, release("v1.5.0")])
            ),
            patch.object(module, "run", side_effect=run),
        ):
            module.publish("owner/repo", IMAGE, "v1.4.2", SHA)
        self.assertEqual(len(calls), 6)
        self.assertIn(f"{IMAGE}:1.4", calls[5])
        self.assertNotIn(f"{IMAGE}:latest", calls[5])
        self.assertNotIn(f"{IMAGE}:1", calls[5])

    def test_waits_for_release_and_requires_valid_identity(self):
        current = release("v1.5.0", draft=True)
        with (
            patch.object(module, "releases", side_effect=[[], [current]]),
            patch.object(module.time, "sleep"),
        ):
            self.assertEqual(
                module.find_release("owner/repo", "v1.5.0", attempts=2)[0], current
            )
        with (
            patch.object(module, "releases", return_value=[]),
            patch.object(module.time, "sleep"),
            self.assertRaises(ValueError),
        ):
            module.find_release("owner/repo", "v1.5.0", attempts=2)
        for tag, sha in [("v1.5", SHA), ("v1.5.0", "bad")]:
            with self.subTest(tag=tag, sha=sha), self.assertRaises(ValueError):
                module.publish("owner/repo", IMAGE, tag, sha)

    def test_prerelease_never_updates_latest_and_must_be_marked_prerelease(self):
        rc = release("v1.5.0-rc.1", draft=True, prerelease=True)
        calls = []

        def run(*args, input_text=None):
            calls.append((args, input_text))
            return inspect_result(args, "v1.5.0-rc.1")

        with (
            patch.object(module, "find_release", return_value=(rc, [rc])),
            patch.object(module, "run", side_effect=run),
        ):
            module.publish("owner/repo", IMAGE, "v1.5.0-rc.1", SHA)
        self.assertEqual(len(calls), 6)
        self.assertEqual(
            json.loads(calls[-1][1]), {"draft": False, "make_latest": "false"}
        )
        with (
            patch.object(
                module,
                "find_release",
                return_value=(release("v1.5.0-rc.1", draft=True), []),
            ),
            self.assertRaises(ValueError),
        ):
            module.publish("owner/repo", IMAGE, "v1.5.0-rc.1", SHA)


if __name__ == "__main__":
    unittest.main()
