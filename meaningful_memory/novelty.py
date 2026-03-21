"""
Novelty Detection — Is this genuinely new?

Three signals:
  1. Semantic distance — how different from what we know
  2. Conceptual novelty — new concepts not seen before
  3. Bridging — does this connect previously unconnected memories

Works standalone with token overlap, or with embeddings
when integrated with a vector store.
"""

import math
from typing import List, Dict, Optional

from .store import MemoryEntry
from .config import NoveltyConfig, default_config


def semantic_distance(
    new_entry: MemoryEntry,
    existing: List[MemoryEntry],
    top_k: int = 5
) -> float:
    """
    How semantically distant is this from what we already know?

    0.0 = identical to existing memories
    1.0 = completely unlike anything stored
    """
    if not existing:
        return 1.0

    new_tokens = new_entry.tokens
    if not new_tokens:
        return 1.0

    similarities = []
    for mem in existing:
        mem_tokens = mem.tokens
        if not mem_tokens:
            continue
        union = new_tokens | mem_tokens
        if not union:
            continue
        overlap = len(new_tokens & mem_tokens) / len(union)
        similarities.append(overlap)

    if not similarities:
        return 1.0

    similarities.sort(reverse=True)
    avg_sim = sum(similarities[:top_k]) / len(similarities[:top_k])

    # sqrt makes moderate distance register more clearly
    return math.sqrt(max(0.0, 1.0 - avg_sim))


def conceptual_novelty(
    new_entry: MemoryEntry,
    existing: List[MemoryEntry],
    sweet_spot: float = 0.3
) -> float:
    """
    Does this memory introduce concepts not seen before?

    Peak novelty is ~30% new concepts. Too much newness
    suggests noise, not insight.

    0.0 = all concepts already exist
    1.0 = optimal ratio of new concepts
    """
    new_tokens = new_entry.tokens
    if not new_tokens:
        return 0.0

    existing_tokens = set()
    for mem in existing:
        existing_tokens.update(mem.tokens)

    novel = new_tokens - existing_tokens
    if not novel:
        return 0.0

    ratio = len(novel) / len(new_tokens)

    if ratio > sweet_spot:
        adjusted = sweet_spot + (ratio - sweet_spot) * 0.3
    else:
        adjusted = ratio

    return min(1.0, adjusted / sweet_spot)


def bridging_score(
    new_entry: MemoryEntry,
    existing: List[MemoryEntry],
    threshold: float = 0.08
) -> float:
    """
    Does this memory connect previously unconnected memories?

    The most interesting memories bridge distant clusters.
    A memory moderately similar to two very different groups
    is a bridge — that's where emergence lives.

    0.0 = connects nothing new
    1.0 = bridges maximally distant clusters
    """
    if len(existing) < 2:
        return 0.0

    new_tokens = new_entry.tokens
    if not new_tokens:
        return 0.0

    connected = []
    for mem in existing:
        shared = new_tokens & mem.tokens
        overlap = len(shared) / max(len(new_tokens), 1)
        if overlap > threshold:
            connected.append(mem)

    if len(connected) < 2:
        return 0.0

    # how different are the connected memories from each other?
    distances = []
    for i in range(len(connected)):
        for j in range(i + 1, len(connected)):
            shared = connected[i].tokens & connected[j].tokens
            union = connected[i].tokens | connected[j].tokens
            overlap = len(shared) / max(len(union), 1)
            distances.append(1.0 - overlap)

    if not distances:
        return 0.0

    avg_distance = sum(distances) / len(distances)

    # cross-sector bonus
    sectors = set(m.sector for m in connected)
    sector_bonus = min(1.0, (len(sectors) - 1) / 2.0)

    return min(1.0, avg_distance * 0.7 + sector_bonus * 0.3)


def compute_novelty(
    new_entry: MemoryEntry,
    existing: List[MemoryEntry],
    config: Optional[NoveltyConfig] = None
) -> Dict[str, float]:
    """
    Composite novelty score.

    Returns dict with individual signals and composite:
    {
        "semantic_distance": 0.0-1.0,
        "conceptual_novelty": 0.0-1.0,
        "bridging": 0.0-1.0,
        "composite": 0.0-1.0,
    }
    """
    cfg = config or default_config.novelty
    w = cfg.weights

    sd = semantic_distance(new_entry, existing, cfg.top_k_neighbors)
    cn = conceptual_novelty(new_entry, existing, cfg.concept_sweet_spot)
    bs = bridging_score(new_entry, existing, cfg.bridge_threshold)

    composite = (
        w["semantic_distance"] * sd +
        w["conceptual_novelty"] * cn +
        w["bridging"] * bs
    )

    return {
        "semantic_distance": round(sd, 4),
        "conceptual_novelty": round(cn, 4),
        "bridging": round(bs, 4),
        "composite": round(min(1.0, composite), 4),
    }
