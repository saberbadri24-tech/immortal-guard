#!/usr/bin/env python3
"""Offline contracts for the official-source review/actionability split."""
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("official_source_gate.py")
SPEC = importlib.util.spec_from_file_location("official_source_gate", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class OfficialSourceGateTests(unittest.TestCase):
    def test_official_reward_without_eligibility_enters_review_not_action(self):
        item = {"id": "review-1", "title": "Open grant rewards", "url": "https://news.google.com/article"}
        verification = {
            "finalUrl": "https://blog.ethereum.org/en/grants",
            "reachable": True, "finalHttps": True, "publicHost": True, "statusCode": 200,
            "rewardSignal": True, "eligibilitySignal": False, "expiredSignal": False, "blockedSignal": False
        }
        row = MOD.evaluate_item(item, verification)
        self.assertEqual(row["qualification"], "OFFICIAL_VERIFIED_REVIEW")
        self.assertTrue(row["reviewable"])
        self.assertFalse(row["actionable"])

    def test_official_reward_with_eligibility_evidence_is_actionable_tier(self):
        item = {"id": "action-1", "title": "Security bounty", "url": "https://immunefi.com/bounty"}
        verification = {
            "finalUrl": "https://immunefi.com/bounty",
            "reachable": True, "finalHttps": True, "publicHost": True, "statusCode": 200,
            "rewardSignal": True, "eligibilitySignal": True, "expiredSignal": False, "blockedSignal": False
        }
        row = MOD.evaluate_item(item, verification)
        self.assertEqual(row["qualification"], "OFFICIAL_VERIFIED_ACTIONABLE")
        self.assertTrue(row["actionable"])

    def test_non_official_final_destination_is_not_qualified(self):
        item = {"id": "news-1", "title": "Airdrop rewards", "url": "https://news.google.com/article"}
        verification = {
            "finalUrl": "https://random-news.example/article",
            "reachable": True, "finalHttps": True, "publicHost": True, "statusCode": 200,
            "rewardSignal": True, "eligibilitySignal": True, "expiredSignal": False, "blockedSignal": False
        }
        row = MOD.evaluate_item(item, verification)
        self.assertFalse(row["reviewable"])
        self.assertEqual(row["qualification"], "DISCOVERY_ONLY")

    def test_testnet_announcement_without_reward_is_not_qualified(self):
        item = {"id": "testnet-1", "title": "Glamsterdam Testnet Announcement", "url": "https://blog.ethereum.org/en/testnet"}
        verification = {
            "finalUrl": "https://blog.ethereum.org/en/testnet",
            "reachable": True, "finalHttps": True, "publicHost": True, "statusCode": 200,
            "rewardSignal": False, "eligibilitySignal": False, "expiredSignal": False, "blockedSignal": False
        }
        self.assertFalse(MOD.evaluate_item(item, verification)["reviewable"])

    def test_expired_or_blocked_item_is_not_qualified(self):
        item = {"id": "blocked-1", "title": "Airdrop rewards", "url": "https://ton.org/rewards"}
        verification = {
            "finalUrl": "https://ton.org/rewards",
            "reachable": True, "finalHttps": True, "publicHost": True, "statusCode": 200,
            "rewardSignal": True, "eligibilitySignal": True, "expiredSignal": True, "blockedSignal": False
        }
        self.assertFalse(MOD.evaluate_item(item, verification)["reviewable"])


if __name__ == "__main__":
    unittest.main()
