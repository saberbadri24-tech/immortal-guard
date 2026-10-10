#!/usr/bin/env python3
"""Offline contract tests for the Immortal Guard specialist swarm."""
import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).with_name("specialist_swarm.py")
SPEC = importlib.util.spec_from_file_location("specialist_swarm", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class SpecialistSwarmTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def test_unqualified_candidate_is_held(self):
        result = MOD.review({"id": "x", "title": "Sample", "url": "https://example.org"}, False, self.now)
        self.assertEqual(result["status"], "HOLD_FOR_EVIDENCE")
        self.assertEqual(result["action"], "NO_ACTION")

    def test_qualified_candidate_is_owner_review_only(self):
        result = MOD.review({"id": "x", "title": "Sample", "url": "https://example.org"}, True, self.now)
        self.assertEqual(result["status"], "READY_FOR_OWNER_REVIEW")
        self.assertEqual(result["action"], "OWNER_REVIEW_ONLY")
        self.assertFalse(result["safety"]["autoSigning"])

    def test_scams_are_blocked(self):
        result = MOD.review({"id": "x", "title": "Phishing drainer", "url": "https://example.org"}, True, self.now)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["action"], "NO_ACTION")

    def test_wallet_secrets_never_pass(self):
        result = MOD.review({"id": "x", "title": "Send seed phrase to claim", "url": "https://example.org"}, True, self.now)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["safety"]["autoClaim"])
        self.assertFalse(result["safety"]["autoTransfer"])

    def test_payload_deduplicates_candidates(self):
        item = {"id": "x", "title": "Sample", "url": "https://example.org"}
        payload = MOD.build_payload({"items": [item]}, {"items": [item]}, {"qualifiedIds": ["x"]})
        self.assertEqual(payload["candidateCount"], 1)
        self.assertEqual(payload["readyForOwnerReview"], 1)
        self.assertEqual(len(payload["agents"]), 6)


if __name__ == "__main__":
    unittest.main()
