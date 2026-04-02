"""Tests for staleness detection."""

import time
import tempfile
import shutil
import unittest

from meaningful_memory.store import MemoryStore, MemoryEntry


class TestStaleness(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_verified_at_starts_none(self):
        entry = self.store.add("test memory")
        self.assertIsNone(entry.verified_at)

    def test_verify_sets_timestamp(self):
        entry = self.store.add("test memory")
        before = time.time()
        verified = self.store.verify(entry.id)
        after = time.time()
        self.assertIsNotNone(verified.verified_at)
        self.assertGreaterEqual(verified.verified_at, before)
        self.assertLessEqual(verified.verified_at, after)

    def test_verify_persists_to_disk(self):
        entry = self.store.add("test memory")
        self.store.verify(entry.id)
        reloaded = self.store.get(entry.id)
        self.assertIsNotNone(reloaded.verified_at)

    def test_verify_nonexistent_returns_none(self):
        result = self.store.verify("nonexistent-id")
        self.assertIsNone(result)

    def test_get_stale_new_memories_not_stale(self):
        self.store.add("fresh memory")
        stale = self.store.get_stale(threshold_days=30)
        self.assertEqual(len(stale), 0)

    def test_get_stale_old_unverified_memories(self):
        entry = self.store.add("old memory")
        # backdate creation
        entry.created_at = time.time() - (31 * 86400)
        self.store.update(entry)
        stale = self.store.get_stale(threshold_days=30)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].id, entry.id)

    def test_get_stale_verified_recently_not_stale(self):
        entry = self.store.add("verified memory")
        entry.created_at = time.time() - (60 * 86400)
        self.store.update(entry)
        self.store.verify(entry.id)
        stale = self.store.get_stale(threshold_days=30)
        self.assertEqual(len(stale), 0)

    def test_get_stale_verified_long_ago_is_stale(self):
        entry = self.store.add("stale verified memory")
        entry.created_at = time.time() - (60 * 86400)
        entry.verified_at = time.time() - (35 * 86400)
        self.store.update(entry)
        stale = self.store.get_stale(threshold_days=30)
        self.assertEqual(len(stale), 1)

    def test_verified_at_in_file_content(self):
        entry = MemoryEntry(content="test", verified_at=1234567890.0)
        content = entry.to_file_content()
        self.assertIn("verified_at: 1234567890.0", content)

    def test_verified_at_roundtrip(self):
        entry = MemoryEntry(content="test", verified_at=1234567890.0)
        content = entry.to_file_content()
        restored = MemoryEntry.from_file_content(content)
        self.assertEqual(restored.verified_at, 1234567890.0)


if __name__ == "__main__":
    unittest.main()
