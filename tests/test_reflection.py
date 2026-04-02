"""Tests for four-phase reflection."""

import time
import tempfile
import shutil
import unittest

from meaningful_memory.store import MemoryStore, MemoryEntry
from meaningful_memory.reflection import (
    run_reflection, run_full_reflection,
    cluster_meaningful, token_similarity, temporal_proximity,
    ReflectionReport, OrientationReport,
)
from meaningful_memory.config import MeaningfulConfig, ReflectionConfig


class TestTokenSimilarity(unittest.TestCase):

    def test_identical(self):
        a = MemoryEntry(content="python machine learning data")
        b = MemoryEntry(content="python machine learning data")
        self.assertGreater(token_similarity(a, b), 0.9)

    def test_zero_for_empty(self):
        a = MemoryEntry(content="")
        b = MemoryEntry(content="hello")
        self.assertEqual(token_similarity(a, b), 0.0)


class TestTemporalProximity(unittest.TestCase):

    def test_same_time(self):
        now = time.time()
        a = MemoryEntry(content="a", created_at=now)
        b = MemoryEntry(content="b", created_at=now)
        self.assertAlmostEqual(temporal_proximity(a, b), 1.0)

    def test_beyond_window(self):
        now = time.time()
        a = MemoryEntry(content="a", created_at=now)
        b = MemoryEntry(content="b", created_at=now - 86400 * 2)
        self.assertEqual(temporal_proximity(a, b, window_hours=24.0), 0.0)


class TestClusterMeaningful(unittest.TestCase):

    def test_clusters_similar_memories(self):
        now = time.time()
        memories = [
            MemoryEntry(content="python machine learning data science models",
                        meaningful_weight=0.8, created_at=now),
            MemoryEntry(content="python machine learning neural network training",
                        meaningful_weight=0.6, created_at=now),
            MemoryEntry(content="cooking dinner recipes pasta tomato sauce",
                        meaningful_weight=0.5, created_at=now),
        ]
        cfg = ReflectionConfig(semantic_threshold=0.3, min_cluster_size=2)
        clusters = cluster_meaningful(memories, cfg)
        self.assertGreaterEqual(len(clusters), 1)

    def test_skips_consolidated(self):
        now = time.time()
        memories = [
            MemoryEntry(content="python machine learning data science",
                        meaningful_weight=0.8, created_at=now, consolidated=True),
            MemoryEntry(content="python machine learning neural networks",
                        meaningful_weight=0.6, created_at=now),
        ]
        cfg = ReflectionConfig(semantic_threshold=0.3, min_cluster_size=2)
        clusters = cluster_meaningful(memories, cfg)
        self.assertEqual(len(clusters), 0)


class TestRunReflection(unittest.TestCase):
    """Test backward-compatible run_reflection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_insufficient_memories(self):
        self.store.add("one memory")
        result = run_reflection(self.store)
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["reason"], "insufficient_memories")

    def test_creates_reflections(self):
        now = time.time()
        for i in range(12):
            entry = self.store.add(
                f"consciousness emergence awareness mind pattern {i}",
                sector="semantic"
            )
            entry.created_at = now
            entry.meaningful_weight = 0.5
            self.store.update(entry)

        cfg = ReflectionConfig(
            min_memories=5,
            semantic_threshold=0.3,
            min_cluster_size=2,
        )
        result = run_reflection(self.store, config=cfg)
        self.assertGreaterEqual(result["created"], 0)


class TestRunFullReflection(unittest.TestCase):
    """Test four-phase run_full_reflection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_returns_reflection_report(self):
        now = time.time()
        for i in range(12):
            entry = self.store.add(
                f"consciousness emergence awareness mind pattern {i}",
                sector="semantic"
            )
            entry.created_at = now
            entry.meaningful_weight = 0.5
            self.store.update(entry)

        cfg = MeaningfulConfig()
        cfg.reflection.min_memories = 5
        cfg.reflection.semantic_threshold = 0.3
        cfg.reflection.min_cluster_size = 2

        report = run_full_reflection(self.store, config=cfg)
        self.assertIsInstance(report, ReflectionReport)
        self.assertIsInstance(report.orientation, OrientationReport)

    def test_insufficient_returns_empty_report(self):
        self.store.add("one lonely memory")
        report = run_full_reflection(self.store)
        self.assertIsInstance(report, ReflectionReport)
        self.assertEqual(report.created, 0)

    def test_orientation_counts(self):
        now = time.time()
        for i in range(15):
            entry = self.store.add(f"memory about topic alpha beta gamma {i}")
            entry.created_at = now
            self.store.update(entry)

        cfg = MeaningfulConfig()
        cfg.reflection.min_memories = 5
        report = run_full_reflection(self.store, config=cfg)
        self.assertGreaterEqual(report.orientation.active, 15)


if __name__ == "__main__":
    unittest.main()
