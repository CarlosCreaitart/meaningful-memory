"""
Contradiction Detection — Surface disagreements, don't bury them.

Scans memories within the same domain and identifies conflicting
conclusions. Two memories about the same topic that disagree
should be surfaced, not silently coexist.

Key design decision: Contradictions are surfaced, not auto-resolved.
The user or a higher-level system decides which to keep.
Automatic resolution is maintenance. Surfacing is meaning.
"""

from dataclasses import dataclass
from typing import List, Optional

from .store import MemoryEntry, MemoryStore
from .config import ContradictionConfig, default_config


# Words that signal negation or opposition
NEGATION_SIGNALS = {
    "not", "never", "no", "none", "neither", "nor", "cannot", "can't",
    "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't",
    "weren't", "shouldn't", "wouldn't", "couldn't", "hardly", "barely",
    "without", "lack", "lacks", "lacking", "failed", "failure", "impossible",
    "unable", "ineffective", "incorrect", "wrong", "false", "bad",
    "worse", "worsens", "decreases", "reduces", "prevents", "blocks",
    "harmful", "dangerous", "useless", "unnecessary", "irrelevant",
}

# Antonym pairs — if memory A uses one side and B uses the other, that's a signal
ANTONYM_PAIRS = [
    ("effective", "ineffective"), ("useful", "useless"),
    ("important", "unimportant"), ("necessary", "unnecessary"),
    ("possible", "impossible"), ("correct", "incorrect"),
    ("improves", "worsens"), ("increases", "decreases"),
    ("helps", "hinders"), ("enables", "prevents"),
    ("better", "worse"), ("success", "failure"),
    ("true", "false"), ("safe", "dangerous"),
    ("fast", "slow"), ("simple", "complex"),
]


@dataclass
class ContradictionPair:
    """A detected contradiction between two memories."""
    memory_a_id: str
    memory_b_id: str
    topic: str
    confidence: float
    suggested_keep: str

    def to_dict(self):
        return {
            "memory_a_id": self.memory_a_id,
            "memory_b_id": self.memory_b_id,
            "topic": self.topic,
            "confidence": round(self.confidence, 4),
            "suggested_keep": self.suggested_keep,
        }


def topic_overlap(a: MemoryEntry, b: MemoryEntry) -> float:
    """How much topical overlap exists between two memories."""
    ta, tb = a.tokens, b.tokens
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def negation_score(a: MemoryEntry, b: MemoryEntry) -> float:
    """
    Detect opposing signals between two memories.

    Checks for:
    1. One memory uses negation words where the other doesn't
    2. Antonym pairs across memories
    """
    tokens_a = set(a.content.lower().split())
    tokens_b = set(b.content.lower().split())

    score = 0.0
    signals = 0

    # asymmetric negation: one memory negates, the other doesn't
    neg_a = tokens_a & NEGATION_SIGNALS
    neg_b = tokens_b & NEGATION_SIGNALS

    if neg_a and not neg_b:
        score += 0.4
        signals += 1
    elif neg_b and not neg_a:
        score += 0.4
        signals += 1

    # antonym detection
    for word_a, word_b in ANTONYM_PAIRS:
        if (word_a in tokens_a and word_b in tokens_b) or \
           (word_b in tokens_a and word_a in tokens_b):
            score += 0.5
            signals += 1
            break  # one antonym pair is enough

    if signals == 0:
        return 0.0

    return min(1.0, score)


def suggest_keep(a: MemoryEntry, b: MemoryEntry) -> str:
    """Suggest which memory to keep based on resonance/weight, not recency."""
    score_a = a.meaningful_weight + (0.5 if a.is_formative else 0.0)
    score_b = b.meaningful_weight + (0.5 if b.is_formative else 0.0)
    return a.id if score_a >= score_b else b.id


def detect_contradictions(
    store: MemoryStore,
    config: Optional[ContradictionConfig] = None,
    verbose: bool = False
) -> List[ContradictionPair]:
    """
    Scan active memories for contradictions.

    Returns pairs of memories that appear to disagree on the same topic.
    These are surfaced for human or system review — not auto-resolved.
    """
    cfg = config or default_config.contradiction
    memories = store.get_all("active", limit=500)
    contradictions = []
    checked = set()

    for i, a in enumerate(memories):
        for j, b in enumerate(memories):
            if i >= j:
                continue
            pair_key = (a.id, b.id)
            if pair_key in checked:
                continue
            checked.add(pair_key)

            # must share enough topic to be comparable
            overlap = topic_overlap(a, b)
            if overlap < cfg.topic_similarity_threshold:
                continue

            # check for opposing signals
            neg = negation_score(a, b)
            if neg == 0.0:
                continue

            # confidence combines topic overlap and negation strength
            confidence = overlap * 0.4 + neg * 0.6

            if confidence < cfg.confidence_threshold:
                continue

            # shared tokens form the topic description
            shared = a.tokens & b.tokens
            topic_str = ", ".join(sorted(shared)[:5]) if shared else "unknown"

            pair = ContradictionPair(
                memory_a_id=a.id,
                memory_b_id=b.id,
                topic=topic_str,
                confidence=confidence,
                suggested_keep=suggest_keep(a, b),
            )
            contradictions.append(pair)

            if verbose:
                print(f"  Contradiction (conf={confidence:.3f}): topic=[{topic_str}]")
                print(f"    A [{a.id[:8]}]: \"{a.content[:60]}...\"")
                print(f"    B [{b.id[:8]}]: \"{b.content[:60]}...\"")
                print(f"    Suggested keep: [{pair.suggested_keep[:8]}]")

    contradictions.sort(key=lambda c: c.confidence, reverse=True)

    if verbose:
        print(f"  Found {len(contradictions)} contradictions")

    return contradictions
