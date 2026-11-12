import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from check_release_pr_files import version_only


class ReleasePrFilesTests(unittest.TestCase):
    def test_release_please_version_changes_skip_build(self):
        changes = [
            ("VERSION", "1.3.2\n", "1.4.0\n"),
            (".release-please-manifest.json", '{".":"1.3.2"}', '{".":"1.4.0"}'),
            ("pyproject.toml", '[project]\nversion="1.3.2"\ndependencies=["foo"]', '[project]\nversion="1.4.0"\ndependencies=["foo"]'),
            ("uv.lock", '[[package]]\nname="beatprints-api"\nversion="1.3.2"', '[[package]]\nname="beatprints-api"\nversion="1.4.0"'),
            ("CHANGELOG.md", "old", "new"),
        ]
        self.assertTrue(version_only(changes))

    def test_dependency_or_other_code_changes_require_build(self):
        for change in [
            ("pyproject.toml", '[project]\nversion="1.3.2"\ndependencies=["foo"]', '[project]\nversion="1.4.0"\ndependencies=["bar"]'),
            ("uv.lock", '[[package]]\nname="beatprints-api"\nversion="1.3.2"\n[[package]]\nname="foo"\nversion="1.0.0"', '[[package]]\nname="beatprints-api"\nversion="1.4.0"\n[[package]]\nname="foo"\nversion="2.0.0"'),
            ("apps/api/Dockerfile", "old", "new"),
            ("VERSION", "1.3.2", "invalid"),
            ("pyproject.toml", "not toml", "also not toml"),
        ]:
            with self.subTest(path=change[0]):
                self.assertFalse(version_only([change]))
        self.assertFalse(version_only([]))


if __name__ == "__main__":
    unittest.main()
