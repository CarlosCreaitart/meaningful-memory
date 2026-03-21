"""
Meaningful Weight — How much does this memory matter?

Three dimensions:
  1. Novelty — how genuinely new was this when it arrived
  2. Recall significance — not frequency, but the *pattern* of recall
  3. Connectivity — how central is this in the web of meaning

Weights adapt by age: young memories judged by novelty,
old memories by recall and connectivity.
"""

import math
import time
from typing import Dict, Optional, List

from .store import MemoryEntry
from .config import WeightConfig, default_config


def recall_significance(
    entry: MemoryEntry,
    config: Optional[WeightConfig] = None
) -> float:
    """
    Not just how often — but when and how a memory is recalled.

    A memory recalled once after six months is more significant than
    one recalled daily for a week then forgotten.

    0.0 = never recalled
    1.0 = sustained, spaced recall pattern
    """
    cfg = config or default_config.weight

    if entry.access_count == 0:
        return 0.0

    age_days = max(0.001, entry.age_days)
    gap_days = max(0.001, entry.gap_days)

    # average interval between accesses
    avg_interval = age_days / max(1, entry.access_count)

    # sustained recall across lifespan
    lifespan = min(1.0, age_days / cfg.age_maturity_days)

    # gap resilience — recalled after long gaps = meaningful
    gap_resilience = 1.0 - math.exp(-avg_interval / cfg.gap_resilience_scale_days)

    # frequency with diminishing returns
    freq = min(1.0, math.log1p(entry.access_count) / math.log1p(cfg.frequency_cap))

    # gentle recency factor
    recency = math.exp(-gap_days / cfg.recency_halflife_days)

    # spacing effect bonus
    spacing_bonus = _spacing_effect(entry.access_history)

    score = (0.15 * freq + 0.30 * gap_resilience + 0.30 * lifespan + 0.25 * recency)
    return min(1.0, max(0.0, score * spacing_bonus))


def _spacing_effect(access_history: List[float]) -> float:
    """
    Memories recalled at increasing intervals are strengthened.

    Returns a multiplier: 1.0 (no bonus) to 1.5 (perfect spacing).
    """
    if len(access_history) < 2:
        return 1.0

    sorted_ts = sorted(access_history)
    intervals = [sorted_ts[i] - sorted_ts[i-1] for i in range(1, len(sorted_ts))]

    if len(intervals) < 2:
        return 1.0

    increasing = sum(1 for i in range(1, len(intervals))
                     if intervals[i] > intervals[i-1] * 0.8)

    spacing_ratio = increasing / (len(intervals) - 1)
    return 1.0 + (spacing_ratio * 0.5)


def connectivity_weight(
    entry: MemoryEntry,
    all_entries: List[MemoryEntry]
) -> float:
    """
    How central is this memory in the web of meaning?

    Heavily connected nodes are hubs — like neurons with
    many synapses. They hold the network together.

    0.0 = isolated
    1.0 = highly connected hub
    """
    if not entry.connections:
        return 0.0

    # connection count with diminishing returns
    count_score = min(1.0, math.log1p(len(entry.connections)) / math.log1p(20))

    # importance of connected memories
    connected_weights = []
    entries_by_id = {e.id: e for e in all_entries}
    for cid in entry.connections:
        connected = entries_by_id.get(cid)
        if connected:
            connected_weights.append(connected.meaningful_weight)

    avg_connected = sum(connected_weights) / len(connected_weights) if connected_weights else 0

    # bidirectionality — mutual connections are stronger
    bidi_count = 0
    for cid in entry.connections:
        connected = entries_by_id.get(cid)
        if connected and entry.id in connected.connections:
            bidi_count += 1
    bidi_score = min(1.0, bidi_count / max(1, len(entry.connections)))

    return min(1.0, (
        0.30 * count_score +
        0.40 * avg_connected +
        0.30 * bidi_score
    ))


def compute_weight(
    entry: MemoryEntry,
    all_entries: List[MemoryEntry],
    config: Optional[WeightConfig] = None
) -> Dict[str, float]:
    """
    Compute all weight signals for a memory.

    Returns dict with individual signals and composite.
    """
    cfg = config or default_config.weight

    recall = recall_significance(entry, cfg)
    connectivity = connectivity_weight(entry, all_entries)

    composite = compute_adaptive_weight(
        entry.novelty_score,
        recall,
        connectivity,
        entry.age_days,
        cfg
    )

    return {
        "novelty": entry.novelty_score,
        "recall_significance": round(recall, 4),
        "connectivity": round(connectivity, 4),
        "composite": round(composite, 4),
    }


def compute_adaptive_weight(
    novelty: float,
    recall: float,
    connectivity: float,
    age_days: float,
    config: Optional[WeightConfig] = None
) -> float:
    """
    Weight that shifts emphasis based on memory age.

    Young: novelty-dominant (did it bring something new?)
    Old: recall/connectivity-dominant (did it prove significant?)
    """
    cfg = config or default_config.weight
    age_factor = min(1.0, age_days / cfg.age_maturity_days)

    yw = cfg.young_weights
    mw = cfg.mature_weights

    w_n = yw["novelty"] * (1.0 - age_factor) + mw["novelty"] * age_factor
    w_r = yw["recall"] * (1.0 - age_factor) + mw["recall"] * age_factor
    w_c = yw["connectivity"] * (1.0 - age_factor) + mw["connectivity"] * age_factor

    return min(1.0, w_n * novelty + w_r * recall + w_c * connectivity)
