"""Tests for contradiction detection."""

import tempfile
import shutil
import unittest

from meaningful_memory.store import MemoryStore, MemoryEntry
from meaningful_memory.contradiction import (
    detect_contradictions, topic_overlap, negation_score,
    suggest_keep, ContradictionPair,
)
from meaningful_memory.config import ContradictionConfig


class TestTopicOverlap(unittest.TestCase):

    def test_high_overlap(self):
        a = MemoryEntry(content="machine learning models improve accuracy")
        b = MemoryEntry(content="machine learning models reduce accuracy")
        overlap = topic_overlap(a, b)
        self.assertGreater(overlap, 0.3)

    def test_no_overlap(self):
        a = MemoryEntry(content="python programming language")
        b = MemoryEntry(content="cooking pasta dinner recipe")
        overlap = topic_overlap(a, b)
        self.assertAlmostEqual(overlap, 0.0, places=1)

    def test_empty_content(self):
        a = MemoryEntry(content="")
        b = MemoryEntry(content="hello world")
        self.assertEqual(topic_overlap(a, b), 0.0)


class TestNegationScore(unittest.TestCase):

    def test_detects_negation(self):
        a = MemoryEntry(content="spaced repetition is effective for learning")
        b = MemoryEntry(content="spaced repetition is not effective for learning")
        score = negation_score(a, b)
        self.assertGreater(score, 0.0)

    def test_detects_antonyms(self):
        a = MemoryEntry(content="this approach improves performance significantly")
        b = MemoryEntry(content="this approach worsens performance significantly")
        score = negation_score(a, b)
        self.assertGreater(score, 0.0)

    def test_no_negation(self):
        a = MemoryEntry(content="python is great for data science")
        b = MemoryEntry(content="python is wonderful for data science")
        score = negation_score(a, b)
        self.assertEqual(score, 0.0)


class TestSuggestKeep(unittest.TestCase):

    def test_higher_weight_wins(self):
        a = MemoryEntry(id="a", content="test", meaningful_weight=0.8)
        b = MemoryEntry(id="b", content="test", meaningful_weight=0.3)
        self.assertEqual(suggest_keep(a, b), "a")

    def test_formative_bonus(self):
        a = MemoryEntry(id="a", content="test", meaningful_weight=0.3, is_formative=True)
        b = MemoryEntry(id="b", content="test", meaningful_weight=0.7)
        self.assertEqual(suggest_keep(a, b), "a")


class TestDetectContradictions(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(path=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_detects_contradiction(self):
        self.store.add("spaced repetition is effective for long term memory retention")
        self.store.add("spaced repetition is not effective for long term memory retention")

        contradictions = detect_contradictions(
            self.store,
            ContradictionConfig(topic_similarity_threshold=0.2, confidence_threshold=0.3)
        )
        self.assertGreater(len(contradictions), 0)

    def test_no_contradiction_different_topics(self):
        self.store.add("python programming language data science")
        self.store.add("cooking dinner recipes pasta")

        contradictions = detect_contradictions(self.store)
        self.assertEqual(len(contradictions), 0)

    def test_contradiction_pair_has_fields(self):
        self.store.add("deep learning models improve classification accuracy")
        self.store.add("deep learning models worsen classification accuracy")

        contradictions = detect_contradictions(
            self.store,
            ContradictionConfig(topic_similarity_threshold=0.2, confidence_threshold=0.2)
        )
        if contradictions:
            c = contradictions[0]
            self.assertIsInstance(c, ContradictionPair)
            self.assertIsNotNone(c.memory_a_id)
            self.assertIsNotNone(c.memory_b_id)
            self.assertIsNotNone(c.topic)
            self.assertGreater(c.confidence, 0)
            self.assertIsNotNone(c.suggested_keep)

    def test_contradiction_to_dict(self):
        pair = ContradictionPair(
            memory_a_id="a", memory_b_id="b",
            topic="test", confidence=0.75, suggested_keep="a"
        )
        d = pair.to_dict()
        self.assertEqual(d["memory_a_id"], "a")
        self.assertEqual(d["confidence"], 0.75)


if __name__ == "__main__":
    unittest.main()
