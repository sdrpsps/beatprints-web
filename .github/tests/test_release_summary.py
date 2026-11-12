import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("release_summary", Path(__file__).parents[1] / "scripts" / "release_summary.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import prepare_release_pr
import validate_pr_notes

NOTES = """## Summary
Internal details
## What's New
<!-- Instructions -->
### 简体中文
- 支持扫码
### 繁體中文
- 支援掃碼
### English
- Scan codes
## Verification
Done
"""


class ReleaseSummaryTests(unittest.TestCase):
    def test_extracts_three_languages_and_excludes_other_sections(self):
        self.assertEqual(module.extract_summary(NOTES), {"zh-CN": "- 支持扫码", "zh-TW": "- 支援掃碼", "en": "- Scan codes"})

    def test_rejects_missing_duplicate_empty_or_mixed_markers(self):
        for body in ("", NOTES.replace("### English", "### Français"), NOTES.replace("- Scan codes", ""), NOTES.replace("- Scan codes", "None"), NOTES.replace("### English", "### English\n- First\n### English")):
            with self.subTest(body=body), self.assertRaises(ValueError):
                module.extract_summary(body)

    def test_internal_changes_require_explicit_markers_in_all_languages(self):
        body = NOTES.replace("- 支持扫码", "None").replace("- 支援掃碼", "None").replace("- Scan codes", "None")
        self.assertEqual(module.extract_summary(body), {"zh-CN": "", "zh-TW": "", "en": ""})

    def test_pr_validation_requires_notes_for_feature_and_release_prs(self):
        script = Path(__file__).parents[1] / "scripts" / "validate_pr_notes.py"
        def validate(body, branch="feature"):
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as event:
                json.dump({"pull_request": {"body": body, "head": {"ref": branch}}}, event)
                event.flush()
                return subprocess.run([sys.executable, str(script)], env={**os.environ, "GITHUB_EVENT_PATH": event.name, "GITHUB_REPOSITORY": "owner/repo"}, capture_output=True).returncode
        self.assertEqual(validate(NOTES), 0)
        self.assertNotEqual(validate("## What's New\n- missing languages"), 0)
        self.assertEqual(validate(module.update_body("## Features", [module.extract_summary(NOTES)]), "release-please--branches--main"), 0)

    def test_release_pr_waits_for_notes_and_fails_on_timeout(self):
        pr = {"number": 25, "body": ""}
        ready = module.update_body("## Features", [module.extract_summary(NOTES)])
        with patch.object(validate_pr_notes.time, "sleep"), patch.object(validate_pr_notes, "gh_json", side_effect=[{"body": ""}, {"body": ready}]) as api:
            self.assertTrue(validate_pr_notes.wait_for_release_summary(pr, "owner/repo", attempts=3))
            self.assertEqual(api.call_count, 2)
        with patch.object(validate_pr_notes.time, "sleep"), patch.object(validate_pr_notes, "gh_json", return_value={"body": ""}):
            self.assertFalse(validate_pr_notes.wait_for_release_summary(pr, "owner/repo", attempts=3))

    def test_release_pr_contains_notes_before_creation_and_is_idempotent(self):
        original = ":robot: Release\n---\n\n\n## [1.4.0](https://example.com) (2026-11-12)\n\n### Features\n\n* feature ([abc](https://example.com))\n\n---\nFooter"
        updated = prepare_release_pr.prepare_body(original, [module.extract_summary(NOTES)])
        self.assertEqual(prepare_release_pr.prepare_body(updated, [module.extract_summary(NOTES)]), updated)
        self.assertLess(updated.index("## [1.4.0]"), updated.index("## 简体中文"))
        self.assertLess(updated.index("## 简体中文"), updated.index("### Features"))
        self.assertIn("* feature ([abc](https://example.com))", updated)
        self.assertTrue(updated.endswith("---\nFooter"))
        with self.assertRaises(ValueError):
            prepare_release_pr.prepare_body("unexpected PR format", [])

    def test_prepares_release_pr_from_merged_feature_notes(self):
        release_pr = {"number": 21, "head": {"ref": "release-please--branches--main"}, "body": ":robot: Release\n---\n\n## [1.4.0](url)\n\n### Features\n\n* feature\n\n---\nFooter"}
        feature_pr = {"number": 20, "merged_at": "2026-01-01", "base": {"ref": "main"}, "body": NOTES}
        calls = []
        def run(*args, input_text=None):
            calls.append((args, input_text))
            if args[:2] == ("git", "describe"): return "v1.3.2"
            if args[:2] == ("git", "rev-list"): return "first"
            return ""
        def gh_json(*args):
            return [[release_pr]] if any(arg.endswith("/pulls") and "commits/" not in arg for arg in args) else [[feature_pr]]
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "DEFAULT_BRANCH": "main"}), patch.object(prepare_release_pr, "run", side_effect=run), patch.object(prepare_release_pr, "gh_json", side_effect=gh_json), patch.object(sys.modules["release_summary"], "run", side_effect=run), patch.object(sys.modules["release_summary"], "gh_json", side_effect=gh_json):
            prepare_release_pr.main()
        args, payload = calls[-1]
        self.assertEqual(args[-3:], ("repos/owner/repo/pulls/21", "--input", "-"))
        body = json.loads(payload)["body"]
        self.assertIn("- 支持扫码", body)
        self.assertIn("### Features\n\n* feature", body)

    def test_updates_idempotently_and_preserves_generated_notes(self):
        original = "## Features\n\n* feature ([abc](https://example.com))"
        summary = module.extract_summary(NOTES)
        updated = module.update_body(original, [summary])
        self.assertEqual(module.update_body(updated, [summary]), updated)
        self.assertIn(original, updated)
        self.assertIn("\n\n---\n" + module.END + "\n\n" + original, updated)
        for lang in module.LANGUAGES:
            self.assertIn(f"<!-- release-summary:{lang}:start -->", updated)
            self.assertIn(summary[lang], updated)
        self.assertIn("No user-visible changes.", module.update_body(original, []))
        self.assertIn(original, module.update_body(updated, []))

    def test_collects_merged_prs_once_and_preserves_release_notes(self):
        pr = {"number": 12, "merged_at": "2026-01-01", "base": {"ref": "main"}, "body": NOTES}
        commands = []
        def run(*args, input_text=None):
            commands.append((args, input_text))
            if args[:2] == ("git", "describe"): return "v1.3.2"
            if args[:2] == ("git", "rev-list"): return "first\nsecond"
            return ""
        def gh_json(*args):
            if any("commits/first/pulls" in arg or "commits/second/pulls" in arg for arg in args): return [[pr]]
            return {"id": 42, "body": "## Features\n- technical"}
        with patch.dict(os.environ, {"RELEASE_TAG": "v1.4.0", "GITHUB_REPOSITORY": "owner/repo", "DEFAULT_BRANCH": "main"}), patch.object(module, "run", side_effect=run), patch.object(module, "gh_json", side_effect=gh_json):
            module.main()
        body = json.loads(commands[-1][1])["body"]
        self.assertEqual(body.count("支持扫码"), 1)
        self.assertIn("technical", body)


if __name__ == "__main__":
    unittest.main()
