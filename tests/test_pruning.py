"""Tests for duplicate pruning."""

import tempfile
import shutil
import unittest

from meaningful_memory.store import MemoryStore, MemoryEntry
from meaningful_memory.pruning import (
    prune_duplicates, find_duplicate_groups, merge_into_anchor, token_similarity,
    PruneReport,
)
from meaningful_memory.config import PruningConfig


class TestTokenSimilarity(unittest.TestCase):

    def test_identical_content(self):
        a = MemoryEntry(content="python is great for data science")
        b = MemoryEntry(content="python is great for data science")
        self.assertGreater(token_similarity(a, b), 0.9)

    def test_completely_different(self):
        a = MemoryEntry(content="python data science machine learning")
        b = MemoryEntry(content="cooking recipes italian pasta dinner")
        self.assertAlmostEqual(token_similarity(a, b), 0.0, places=1)

    def test_empty_content(self):
        a = MemoryEntry(content="")
        b = MemoryEntry(content="hello world")
        self.assertEqual(token_similarity(a, b), 0.0)

    def test_partial_overlap(self):
        a = MemoryEntry(content="python machine learning models")
        b = MemoryEntry(content="python deep learning neural networks")
        sim = token_similarity(a, b)
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)


class TestFindDuplicateGroups(unittest.TestCase):

    def test_finds_duplicates(self):
        memories = [
            MemoryEntry(content="python is great for data science projects", meaningful_weight=0.8),
            MemoryEntry(content="python is great for data science work", meaningful_weight=0.5),
            MemoryEntry(content="cooking recipes require fresh ingredients", meaningful_weight=0.3),
        ]
        groups = find_duplicate_groups(memories, similarity_threshold=0.5)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_no_duplicates(self):
        memories = [
            MemoryEntry(content="python data science machine learning"),
            MemoryEntry(content="cooking recipes italian pasta dinner"),
            MemoryEntry(content="astronomy stars planets galaxies universe"),
        ]
        groups = find_duplicate_groups(memories, similarity_threshold=0.85)
        self.assertEqual(len(groups), 0)

    def test_highest_weight_anchors(self):
        memories = [
            MemoryEntry(content="python is great for data science projects", meaningful_weight=0.3),
            MemoryEntry(content="python is great for data science work", meaningful_weight=0.9),
        ]
        groups = find_duplicate_groups(memories, similarity_threshold=0.5)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0].meaningful_weight, 0.9)


class TestMergeIntoAnchor(unittest.TestCase):

    def test_merges_connections(self):
        anchor = MemoryEntry(content="test", connections=["a", "b"])
        dup = MemoryEntry(content="test dup", connections=["b", "c"])
        merge_into_anchor(anchor, [dup])
        self.assertIn("a", anchor.connections)
        self.assertIn("c", anchor.connections)

    def test_merges_tags(self):
        anchor = MemoryEntry(content="test", tags=["tag1"])
        dup = MemoryEntry(content="test dup", tags=["tag2"])
        merge_into_anchor(anchor, [dup])
        self.assertIn("tag1", anchor.tags)
        self.assertIn("tag2", anchor.tags)

    def test_formative_propagates(self):
        anchor = MemoryEntry(content="test", is_formative=False)
        dup = MemoryEntry(content="test dup", is_formative=True)
        merge_into_anchor(anchor, [dup])
        self.assertTrue(anchor.is_formative)

    def test_access_count_accumulates(self):
        anchor = MemoryEntry(content="test", access_count=3)
        dup = MemoryEntry(content="test dup", access_count=5)
        merge_into_anchor(anchor, [dup])
        self.assertEqual(anchor.access_count, 8)

    def test_pruned_count_tracked(self):
        anchor = MemoryEntry(content="test")
        dup = MemoryEntry(content="test dup")
        merge_into_anchor(anchor, [dup])
        self.assertEqual(anchor.metadata["pruned_count"], 1)

    def test_removes_self_references(self):
        anchor = MemoryEntry(id="anchor-id", content="test", connections=[])
        dup = MemoryEntry(id="dup-id", content="test dup", connections=["anchor-id"])
        merge_into_anchor(anchor, [dup])
        self.assertNotIn("anchor-id", anchor.connections)
        self.assertNotIn("dup-id", anchor.connections)


class TestPruneDuplicates(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_prunes_duplicates_from_store(self):
        self.store.add("python is excellent for data science projects")
        self.store.add("python is excellent for data science work")
        self.store.add("cooking recipes require fresh quality ingredients")

        report = prune_duplicates(self.store, PruningConfig(similarity_threshold=0.5))
        self.assertEqual(report.groups_found, 1)
        self.assertEqual(report.memories_pruned, 1)
        self.assertEqual(len(report.anchors), 1)

    def test_dry_run_no_changes(self):
        self.store.add("python is excellent for data science projects")
        self.store.add("python is excellent for data science work")

        initial_count = self.store.count
        report = prune_duplicates(self.store, PruningConfig(similarity_threshold=0.5), dry_run=True)
        self.assertEqual(report.groups_found, 1)
        self.assertEqual(self.store.count, initial_count)

    def test_pruned_moved_to_pruned_dir(self):
        self.store.add("python is excellent for data science projects")
        self.store.add("python is excellent for data science work")

        report = prune_duplicates(self.store, PruningConfig(similarity_threshold=0.5))

        # one entry should have been pruned
        self.assertEqual(report.memories_pruned, 1)
        # pruned file should exist in pruned/
        import os
        pruned_files = os.listdir(os.path.join(self.tmpdir, "pruned"))
        self.assertEqual(len(pruned_files), 1)


if __name__ == "__main__":
    unittest.main()
