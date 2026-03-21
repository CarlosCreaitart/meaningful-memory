"""
Cognitive Decay — Meaningful forgetting.

Inspired by the Ebbinghaus forgetting curve and the observation
that significant memories resist decay in ways flat exponential
functions can't capture.

Key principles:
  1. Meaningful memories decay slower (weight modulates rate)
  2. Formative memories get protection (they spawned insights)
  3. Memories fade through stages, never hard-deleted
  4. Spacing effect: spaced recall strengthens stability
"""

import math
import time
from typing import Dict, Any, Optional, List

from .store import MemoryEntry, MemoryStore
from .weight import compute_weight
from .config import DecayConfig, default_config


def ebbinghaus_decay(
    strength: float,
    time_days: float,
    stability: float = 1.0,
    config: Optional[DecayConfig] = None
) -> float:
    """
    Ebbinghaus-inspired forgetting curve.

    Higher stability = much slower decay.
      stability=0.3 → half-life ~1.5 days (routine, fades fast)
      stability=1.0 → half-life ~5 days (normal)
      stability=2.5 → half-life ~12.5 days (significant)
      stability=6.0 → half-life ~30 days (formative, persists)

    Memories never fully reach zero — there's always a trace.
    """
    cfg = config or default_config.decay

    if time_days <= 0:
        return strength

    effective_stability = cfg.base_stability_days * max(0.1, stability)
    retrievability = math.exp(-time_days / effective_stability)

    floor = strength * cfg.trace_floor_ratio
    return max(floor, floor + (strength - floor) * retrievability)


def compute_stability(entry: MemoryEntry, config: Optional[DecayConfig] = None) -> float:
    """
    Compute stability parameter from meaningful weight and formative status.

    High weight = high stability = slow decay.
    Formative memories get additional protection.
    """
    cfg = config or default_config.decay

    base_stability = entry.meaningful_weight

    if entry.is_formative:
        protection = 1.0 + (entry.meaningful_weight * cfg.max_formative_protection)
        return base_stability * protection

    return max(0.1, base_stability)


def compute_decay_rate(
    base_lambda: float,
    meaningful_weight: float,
    config: Optional[DecayConfig] = None
) -> float:
    """
    Weight-modulated decay rate.

    High weight → decay rate drops to 20% of base.
    Low weight → decay rate rises to 150% of base.
    """
    cfg = config or default_config.decay

    modifier = cfg.decay_ceiling - (cfg.decay_weight_factor * meaningful_weight)
    adjusted = base_lambda * modifier

    return max(cfg.min_lambda, min(cfg.max_lambda, adjusted))


def apply_decay(
    entry: MemoryEntry,
    config: Optional[DecayConfig] = None
) -> Dict[str, Any]:
    """
    Apply cognitive decay to a single memory.

    Returns a report of what changed.
    """
    cfg = config or default_config.decay

    stability = compute_stability(entry, cfg)
    old_salience = entry.salience

    new_salience = ebbinghaus_decay(
        strength=old_salience,
        time_days=entry.gap_days,
        stability=stability,
        config=cfg
    )

    # determine state
    state = "active"
    if new_salience < cfg.fading_threshold:
        state = "fading"
    if new_salience < cfg.trace_threshold:
        state = "trace"

    changed = abs(new_salience - old_salience) > 0.001

    if changed:
        entry.salience = new_salience
        entry.decay_state = state

    return {
        "memory_id": entry.id,
        "old_salience": round(old_salience, 4),
        "new_salience": round(new_salience, 4),
        "stability": round(stability, 4),
        "state": state,
        "is_formative": entry.is_formative,
        "changed": changed,
    }


def run_decay_cycle(
    store: MemoryStore,
    config: Optional[DecayConfig] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a full decay cycle across all active memories.
    """
    cfg = config or default_config.decay
    entries = store.get_all("active", limit=500)
    all_entries = entries  # for weight calculation

    results = {
        "processed": 0,
        "changed": 0,
        "moved_to_fading": 0,
        "formative_protected": 0,
        "states": {"active": 0, "fading": 0, "trace": 0},
    }

    # sample based on ratio
    sample_size = max(1, int(len(entries) * cfg.sample_ratio))
    # prioritize entries not recently decayed
    entries.sort(key=lambda e: e.last_accessed)
    batch = entries[:sample_size]

    for entry in batch:
        # recalculate weight before decay
        weight_result = compute_weight(entry, all_entries)
        entry.meaningful_weight = weight_result["composite"]
        entry.recall_significance = weight_result["recall_significance"]
        entry.connectivity_weight = weight_result["connectivity"]

        report = apply_decay(entry, cfg)
        results["processed"] += 1

        if report["changed"]:
            results["changed"] += 1
            store.update(entry)

            if report["state"] == "fading":
                store.move_to_fading(entry.id)
                results["moved_to_fading"] += 1

        if report["is_formative"]:
            results["formative_protected"] += 1

        results["states"][report["state"]] = results["states"].get(report["state"], 0) + 1

        if verbose:
            print(f"  [{entry.id[:8]}] sal={report['old_salience']:.3f}→{report['new_salience']:.3f} "
                  f"stability={report['stability']:.2f} state={report['state']}"
                  f"{' [FORMATIVE]' if report['is_formative'] else ''}")

    if verbose:
        print(f"\n  Decay cycle: {results['changed']}/{results['processed']} changed, "
              f"{results['formative_protected']} formative protected")

    return results
