import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "updates" / "information-manifest.json"
FEED = ROOT / "updates" / "information-feeds" / "national-tax-2026.json"


class InformationSourceDistributionTests(unittest.TestCase):
    def test_manifest_and_feed_are_safe_public_https_artifacts(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        feed = json.loads(FEED.read_text(encoding="utf-8"))

        self.assertEqual(manifest["manifest_version"], 1)
        self.assertEqual(manifest["version"], "2026.07.13")
        self.assertEqual(len(manifest["sources"]), 1)
        source = manifest["sources"][0]
        self.assertEqual(source["id"], "national-tax-2026")
        self.assertEqual(source["reliability"], "official")
        self.assertEqual(source["region"], "全国")
        self.assertTrue(source["enabled"])
        self.assertGreaterEqual(source["ttl_hours"], 1)
        self.assertLessEqual(source["ttl_hours"], 720)
        manifest_source_url = urlparse(source["url"])
        self.assertEqual(manifest_source_url.scheme, "https")
        self.assertEqual(manifest_source_url.hostname, "raw.githubusercontent.com")

        self.assertGreaterEqual(len(feed["articles"]), 5)
        article_ids = [article["id"] for article in feed["articles"]]
        self.assertEqual(len(article_ids), len(set(article_ids)))

        required_fields = {
            "id",
            "title",
            "source",
            "category",
            "region",
            "published_at",
            "updated_at",
            "source_url",
            "keywords",
            "summary",
            "content",
            "reliability",
        }
        for article in feed["articles"]:
            self.assertTrue(required_fields.issubset(article))
            self.assertEqual(article["reliability"], "official")
            self.assertTrue(article["summary"].strip())
            self.assertTrue(article["content"].strip())
            parsed = urlparse(article["source_url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(
                parsed.hostname == "chinatax.gov.cn"
                or parsed.hostname.endswith(".chinatax.gov.cn")
            )

        serialized = json.dumps(
            {"manifest": manifest, "feed": feed},
            ensure_ascii=False,
        ).lower()
        for forbidden in (
            "company_name",
            "account_set_id",
            "session_token",
            "localappdata",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
