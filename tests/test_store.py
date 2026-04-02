"""Tests for store operations including size-aware management."""

import time
import tempfile
import shutil
import unittest

from meaningful_memory.store import MemoryStore, MemoryEntry
from meaningful_memory.config import MeaningfulConfig


class TestMemoryEntry(unittest.TestCase):

    def test_auto_id(self):
        entry = MemoryEntry(content="test")
        self.assertTrue(len(entry.id) > 0)

    def test_auto_timestamps(self):
        entry = MemoryEntry(content="test")
        self.assertGreater(entry.created_at, 0)
        self.assertEqual(entry.created_at, entry.last_accessed)

    def test_tokens_exclude_stopwords(self):
        entry = MemoryEntry(content="the cat is on the mat")
        tokens = entry.tokens
        self.assertNotIn("the", tokens)
        self.assertNotIn("is", tokens)
        self.assertNotIn("on", tokens)
        self.assertIn("cat", tokens)
        self.assertIn("mat", tokens)

    def test_record_access(self):
        entry = MemoryEntry(content="test")
        entry.record_access()
        self.assertEqual(entry.access_count, 1)
        self.assertEqual(len(entry.access_history), 1)

    def test_to_dict_roundtrip(self):
        entry = MemoryEntry(content="test", sector="episodic", tags=["tag1"])
        d = entry.to_dict()
        restored = MemoryEntry.from_dict(d)
        self.assertEqual(restored.content, "test")
        self.assertEqual(restored.sector, "episodic")
        self.assertEqual(restored.tags, ["tag1"])

    def test_file_content_roundtrip(self):
        entry = MemoryEntry(
            content="test memory content",
            sector="semantic",
            tags=["ai", "memory"],
            connections=["abc", "def"],
            meaningful_weight=0.75,
            is_formative=True,
            verified_at=1234567890.0,
        )
        text = entry.to_file_content()
        restored = MemoryEntry.from_file_content(text)
        self.assertEqual(restored.content, "test memory content")
        self.assertEqual(restored.sector, "semantic")
        self.assertEqual(restored.meaningful_weight, 0.75)
        self.assertTrue(restored.is_formative)
        self.assertEqual(restored.verified_at, 1234567890.0)


class TestMemoryStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_add_and_get(self):
        entry = self.store.add("hello world")
        retrieved = self.store.get(entry.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "hello world")

    def test_get_nonexistent(self):
        self.assertIsNone(self.store.get("nonexistent"))

    def test_get_all(self):
        self.store.add("memory one")
        self.store.add("memory two")
        all_mems = self.store.get_all("active")
        self.assertEqual(len(all_mems), 2)

    def test_update(self):
        entry = self.store.add("original content")
        entry.meaningful_weight = 0.99
        self.store.update(entry)
        reloaded = self.store.get(entry.id)
        self.assertAlmostEqual(reloaded.meaningful_weight, 0.99, places=2)

    def test_move_to_fading(self):
        entry = self.store.add("fading memory")
        self.store.move_to_fading(entry.id)
        active = self.store.get_all("active")
        fading = self.store.get_all("fading")
        self.assertEqual(len(active), 0)
        self.assertEqual(len(fading), 1)

    def test_move_to_pruned(self):
        entry = self.store.add("duplicate memory")
        self.store.move_to_pruned(entry.id)
        self.assertIsNone(self.store.get(entry.id))
        import os
        pruned = os.listdir(os.path.join(self.tmpdir, "pruned"))
        self.assertEqual(len(pruned), 1)

    def test_connect(self):
        a = self.store.add("memory a")
        b = self.store.add("memory b")
        self.store.connect(a.id, b.id)
        a_reloaded = self.store.get(a.id)
        b_reloaded = self.store.get(b.id)
        self.assertIn(b.id, a_reloaded.connections)
        self.assertIn(a.id, b_reloaded.connections)

    def test_search(self):
        self.store.add("python machine learning data science")
        self.store.add("cooking pasta dinner recipe")
        results = self.store.search("python data")
        self.assertGreater(len(results), 0)
        self.assertIn("python", results[0].content)

    def test_count(self):
        self.store.add("one")
        self.store.add("two")
        self.assertEqual(self.store.count, 2)

    def test_stats(self):
        self.store.add("memory", sector="semantic")
        stats = self.store.stats()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["active"], 1)
        self.assertIn("semantic", stats["sectors"])

    def test_creates_pruned_dir(self):
        import os
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "pruned")))


class TestSizeAwareStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config = MeaningfulConfig()
        self.config.store.max_active_memories = 20
        self.config.store.consolidation_trigger = 0.9
        self.config.store.auto_consolidate = True
        self.config.reflection.min_memories = 5
        self.config.reflection.semantic_threshold = 0.3
        self.config.reflection.min_cluster_size = 2
        self.store = MemoryStore(path=self.tmpdir, config=self.config)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_store_accepts_config(self):
        self.assertIsNotNone(self.store._config)

    def test_no_crash_on_consolidation_trigger(self):
        """Adding enough memories to trigger consolidation shouldn't crash."""
        for i in range(20):
            self.store.add(f"memory about topic alpha beta gamma {i}")
        # if we got here without crashing, consolidation works
        self.assertGreater(self.store.count, 0)


if __name__ == "__main__":
    unittest.main()
