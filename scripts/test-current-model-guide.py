#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guide", ROOT / "scripts" / "generate-current-model-guide.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_payload():
    return {
        "schema_version": 2,
        "generated_at": "2026-08-23T20:56:17+00:00",
        "machine": "Apple Silicon test machine",
        "summary": {},
        "installed_models": [{
            "build_id": "mlx:test/model",
            "label": "Test model",
            "runtime": "mlx",
            "model_name": "test/model",
            "source_url": "https://huggingface.co/test/model",
            "benchmark": None,
        }],
        "aliases": [],
        "previously_tested": [],
        "score_definition": "local fixture",
    }


class PublicGuideValidationTests(unittest.TestCase):
    def test_accepts_dated_public_payload(self):
        self.assertEqual(MODULE.validate_public_payload(valid_payload()), [])

    def test_rejects_private_field(self):
        payload = valid_payload()
        payload["private_cache_path"] = "/private/cache"
        self.assertTrue(any("unexpected top-level" in error for error in MODULE.validate_public_payload(payload)))

    def test_rejects_future_or_wrong_schema_date(self):
        payload = valid_payload()
        payload["schema_version"] = 1
        payload["generated_at"] = "not-a-date"
        errors = MODULE.validate_public_payload(payload)
        self.assertTrue(any("schema_version" in error for error in errors))
        self.assertTrue(any("ISO-8601" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
