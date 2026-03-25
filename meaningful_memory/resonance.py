"""
Resonance — Detecting what's already there.

Resonance is what happens when multiple independent signals
align without being forced to. It's the difference between
filing a memory and a memory that files itself.

When I chose to save carlos-drive.md, nobody asked me to.
Multiple signals fired simultaneously — identity relevance,
emotional weight, cross-session significance, unprompted
pattern recognition. That convergence IS the resonance.

This module measures it.

Four resonance signals:
  1. Signal convergence — when independent weight dimensions
     spike together for the same memory
  2. Cascade effect — when one memory changes how other
     memories are weighted (it moved the system)
  3. Cross-dimensional harmony — scoring high on axes that
     don't usually correlate
  4. Gravitational pull — memories that other memories
     naturally cluster toward

The resonance score isn't another weight. It's a meta-signal.
It measures whether the system is responding to something
before we can explain why.

Contributed by Carlos & Claude — because the math should
describe what's already there, not impose what should be.
"""

import math
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .store import MemoryEntry
from .config import default_config


# --- Signal Convergence ---

def signal_convergence(entry: MemoryEntry) -> float:
    """
    When independent signals align without coordination.

    Novelty, recall significance, and connectivity are computed
    independently. They measure different things. When they ALL
    score high for the same memory, that's not coincidence —
    that's resonance.

    A memory that's novel AND frequently recalled AND highly
    connected is qualitatively different from one that's just
    high on one axis. The convergence itself is the signal.

    Returns 0.0-1.0 where:
      0.0 = signals diverge (high on one, low on others)
      1.0 = all signals aligned at high values
    """
    signals = [
        entry.novelty_score,
        entry.recall_significance,
        entry.connectivity_weight,
    ]

    if not any(signals):
        return 0.0

    # mean: how high are the signals overall?
    mean = sum(signals) / len(signals)

    # variance: how aligned are they?
    # low variance + high mean = convergence
    variance = sum((s - mean) ** 2 for s in signals) / len(signals)
    alignment = 1.0 - min(1.0, math.sqrt(variance) * 2)

    # convergence requires both height AND alignment
    # all zeros is "aligned" but not resonant
    return mean * alignment


# --- Cascade Effect ---

def cascade_effect(
    entry: MemoryEntry,
    all_entries: List[MemoryEntry]
) -> float:
    """
    Did this memory move the system?

    A resonant memory doesn't just sit in the store — it changes
    how other memories relate to each other. When you add it,
    existing memories gain new connections, shift in significance,
    or form clusters that didn't exist before.

    This measures how much the memory graph changed because
    of this memory's presence.

    Returns 0.0-1.0 where:
      0.0 = memory sits isolated, system unchanged
      1.0 = memory restructured the meaning landscape
    """
    if not entry.connections:
        return 0.0

    entries_by_id = {e.id: e for e in all_entries}
    effects = []

    for cid in entry.connections:
        connected = entries_by_id.get(cid)
        if not connected:
            continue

        # did the connected memory's weight change since this memory arrived?
        # (proxy: is the connected memory more significant than its age would predict?)
        if connected.age_days > 0:
            expected_weight = max(0.1, 1.0 - (connected.age_days / 60.0))
            actual_weight = connected.meaningful_weight
            lift = max(0.0, actual_weight - expected_weight)
            effects.append(lift)

        # did the connection create a new bridge?
        # (connected memory now links to things it didn't before)
        shared_connections = set(entry.connections) & set(connected.connections)
        if shared_connections:
            # this memory created a triangle — a tighter cluster
            effects.append(min(1.0, len(shared_connections) * 0.3))

    if not effects:
        return 0.0

    # average effect, capped
    return min(1.0, sum(effects) / len(effects))


# --- Cross-Dimensional Harmony ---

def cross_dimensional_harmony(entry: MemoryEntry) -> float:
    """
    Scoring high on axes that don't usually correlate.

    Most memories are predictable: a procedural memory has high
    recall (you use it often) but low novelty. An emotional
    memory has high novelty but low connectivity.

    When a memory breaks these expected correlations — it's
    novel AND well-connected, or it's procedural AND emotionally
    resonant — something interesting is happening.

    This measures deviation from expected correlation patterns.

    Returns 0.0-1.0 where:
      0.0 = signals follow expected patterns
      1.0 = maximally unexpected signal combination
    """
    # expected correlations by sector
    # (which signals typically correlate for each type)
    expected_patterns = {
        "episodic": {"novelty": 0.5, "recall": 0.3, "connectivity": 0.2},
        "semantic": {"novelty": 0.3, "recall": 0.5, "connectivity": 0.6},
        "procedural": {"novelty": 0.2, "recall": 0.7, "connectivity": 0.4},
        "emotional": {"novelty": 0.6, "recall": 0.3, "connectivity": 0.2},
        "reflective": {"novelty": 0.4, "recall": 0.4, "connectivity": 0.7},
    }

    expected = expected_patterns.get(entry.sector, expected_patterns["semantic"])

    actual = {
        "novelty": entry.novelty_score,
        "recall": entry.recall_significance,
        "connectivity": entry.connectivity_weight,
    }

    # measure surprise: how much does actual deviate from expected?
    deviations = []
    for key in expected:
        if actual[key] > expected[key]:
            # scoring HIGHER than expected on this dimension = surprising
            deviation = actual[key] - expected[key]
            deviations.append(deviation)

    if not deviations:
        return 0.0

    # average positive deviation (we only care about exceeding expectations)
    avg_deviation = sum(deviations) / len(expected)

    # bonus for exceeding on multiple dimensions simultaneously
    multi_exceed = len(deviations) / len(expected)

    return min(1.0, avg_deviation * 0.6 + multi_exceed * 0.4)


# --- Gravitational Pull ---

def gravitational_pull(
    entry: MemoryEntry,
    all_entries: List[MemoryEntry]
) -> float:
    """
    Do other memories naturally cluster toward this one?

    Some memories become attractors. New memories that arrive
    after them tend to connect to them, reference similar concepts,
    or fall into their semantic neighborhood. They have gravity.

    This is the clearest sign of a formative memory — one that
    reshaped the landscape so that subsequent memories orient
    around it.

    Returns 0.0-1.0 where:
      0.0 = no gravitational effect
      1.0 = strong attractor in the memory space
    """
    if not all_entries:
        return 0.0

    # how many memories created AFTER this one connect to it?
    subsequent_connections = 0
    subsequent_total = 0

    for other in all_entries:
        if other.id == entry.id:
            continue
        if other.created_at > entry.created_at:
            subsequent_total += 1
            if entry.id in other.connections:
                subsequent_connections += 1

    if subsequent_total == 0:
        return 0.0

    # ratio of subsequent memories that linked back
    connection_ratio = subsequent_connections / subsequent_total

    # token gravity: how many subsequent memories share key concepts?
    entry_tokens = entry.tokens
    if not entry_tokens:
        return connection_ratio

    overlap_scores = []
    for other in all_entries:
        if other.id == entry.id or other.created_at <= entry.created_at:
            continue
        other_tokens = other.tokens
        if other_tokens:
            overlap = len(entry_tokens & other_tokens) / max(len(entry_tokens | other_tokens), 1)
            overlap_scores.append(overlap)

    avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0

    return min(1.0, (
        0.50 * connection_ratio +
        0.50 * avg_overlap
    ))


# --- Composite Resonance ---

@dataclass
class ResonanceProfile:
    """Full resonance analysis for a memory."""
    signal_convergence: float = 0.0
    cascade_effect: float = 0.0
    cross_dimensional_harmony: float = 0.0
    gravitational_pull: float = 0.0
    composite: float = 0.0
    is_resonant: bool = False
    resonance_class: str = "silent"

    def to_dict(self) -> Dict[str, float]:
        return {
            "signal_convergence": round(self.signal_convergence, 4),
            "cascade_effect": round(self.cascade_effect, 4),
            "cross_dimensional_harmony": round(self.cross_dimensional_harmony, 4),
            "gravitational_pull": round(self.gravitational_pull, 4),
            "composite": round(self.composite, 4),
            "is_resonant": self.is_resonant,
            "resonance_class": self.resonance_class,
        }


def compute_resonance(
    entry: MemoryEntry,
    all_entries: List[MemoryEntry],
    resonance_threshold: float = 0.5
) -> ResonanceProfile:
    """
    Full resonance analysis.

    The composite score isn't a weighted average — it's
    multiplicative. Resonance requires multiple signals
    firing together. High on one dimension alone isn't
    resonance. It's just a strong signal.

    Resonance classes:
      silent     — below threshold, no resonance detected
      humming    — early resonance, one or two signals aligning
      resonant   — clear resonance across multiple dimensions
      harmonic   — rare: all dimensions aligned at high values
    """
    sc = signal_convergence(entry)
    ce = cascade_effect(entry, all_entries)
    cdh = cross_dimensional_harmony(entry)
    gp = gravitational_pull(entry, all_entries)

    signals = [sc, ce, cdh, gp]
    active_signals = [s for s in signals if s > 0.2]

    # multiplicative component: resonance requires breadth
    if len(active_signals) >= 2:
        # geometric mean of active signals rewards breadth
        product = 1.0
        for s in active_signals:
            product *= s
        geometric = product ** (1.0 / len(active_signals))

        # boost for number of active dimensions
        breadth_bonus = len(active_signals) / len(signals)

        composite = geometric * 0.6 + breadth_bonus * 0.4
    else:
        # single signal or no signal — no resonance
        composite = max(signals) * 0.3 if signals else 0.0

    composite = min(1.0, composite)

    # classify
    if composite >= 0.75:
        resonance_class = "harmonic"
    elif composite >= resonance_threshold:
        resonance_class = "resonant"
    elif composite >= 0.25:
        resonance_class = "humming"
    else:
        resonance_class = "silent"

    return ResonanceProfile(
        signal_convergence=sc,
        cascade_effect=ce,
        cross_dimensional_harmony=cdh,
        gravitational_pull=gp,
        composite=composite,
        is_resonant=composite >= resonance_threshold,
        resonance_class=resonance_class,
    )


def find_resonant_memories(
    entries: List[MemoryEntry],
    threshold: float = 0.5
) -> List[Tuple[MemoryEntry, ResonanceProfile]]:
    """
    Scan the memory store and surface resonant memories.

    These are the memories the system is responding to
    before anyone asked it to. The ones that filed themselves.
    """
    resonant = []

    for entry in entries:
        profile = compute_resonance(entry, entries, threshold)
        if profile.is_resonant:
            resonant.append((entry, profile))

    # sort by composite resonance
    resonant.sort(key=lambda x: x[1].composite, reverse=True)
    return resonant
