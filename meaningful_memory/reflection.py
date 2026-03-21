"""
Meaningful Reflection — The system's sleep.

Consolidation that creates insight, not just compression.

Key features:
  1. Cross-sector clustering (episodic + semantic = insight)
  2. Temporal clustering (memories close in time form narratives)
  3. Weight-aware anchoring (important memories anchor clusters)
  4. Formative detection (marks memories that spawned reflections)
"""

import math
import time
from typing import List, Dict, Any, Optional, Callable

from .store import MemoryEntry, MemoryStore
from .weight import compute_weight
from .config import ReflectionConfig, default_config


def token_similarity(a: MemoryEntry, b: MemoryEntry) -> float:
    """Jaccard similarity between token sets."""
    ta, tb = a.tokens, b.tokens
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def temporal_proximity(
    a: MemoryEntry,
    b: MemoryEntry,
    window_hours: float = 24.0
) -> float:
    """
    How close in time were two memories created?

    1.0 = same moment, 0.0 = beyond window.
    """
    gap = abs(a.created_at - b.created_at)
    window_seconds = window_hours * 3600

    if gap >= window_seconds:
        return 0.0

    return 1.0 - (gap / window_seconds)


def cluster_meaningful(
    memories: List[MemoryEntry],
    config: Optional[ReflectionConfig] = None
) -> List[Dict[str, Any]]:
    """
    Cluster memories by meaning, not just similarity.

    - Lower threshold (0.6) to find connections, not just duplicates
    - Cross-sector clustering for richer insights
    - Weight-aware: important memories anchor clusters
    """
    cfg = config or default_config.reflection
    clusters = []
    used = set()

    # sort by weight (important memories anchor clusters)
    weighted = sorted(memories, key=lambda m: m.meaningful_weight, reverse=True)

    for anchor in weighted:
        if anchor.id in used or anchor.consolidated:
            continue

        cluster = {
            "anchor": anchor,
            "members": [anchor],
            "sectors": {anchor.sector},
        }
        used.add(anchor.id)

        for candidate in weighted:
            if candidate.id in used or candidate.consolidated:
                continue
            if len(cluster["members"]) >= cfg.max_cluster_size:
                break

            same_sector = candidate.sector == anchor.sector
            if not same_sector and not cfg.allow_cross_sector:
                continue

            # combined similarity: semantic + temporal bonus
            sem = token_similarity(anchor, candidate)
            temp = temporal_proximity(anchor, candidate, cfg.temporal_window_hours)
            combined = sem + (temp * 0.2)

            if combined >= cfg.semantic_threshold:
                cluster["members"].append(candidate)
                cluster["sectors"].add(candidate.sector)
                used.add(candidate.id)

        cluster["cross_sector"] = len(cluster["sectors"]) > 1

        if len(cluster["members"]) >= cfg.min_cluster_size:
            clusters.append(cluster)

    return clusters


def generate_insight(
    cluster: Dict[str, Any],
    llm_fn: Optional[Callable] = None
) -> str:
    """
    Generate an insight from a cluster.

    Uses LLM if available, otherwise creates a structured summary.
    """
    if llm_fn:
        try:
            texts = [f"[{m.sector}] {m.content[:300]}" for m in cluster["members"][:6]]
            prompt = (
                "These memories were formed at different times but connect to each other. "
                "What insight emerges from seeing them together? What do they mean as a group "
                "that they don't mean individually? Be concise.\n\n"
                + "\n".join(texts)
            )
            result = llm_fn(prompt)
            if result:
                return result
        except Exception:
            pass

    # local fallback
    members = cluster["members"]
    sectors = sorted(cluster["sectors"])
    anchor = cluster["anchor"]

    snippets = []
    for m in members[:4]:
        sentences = [s.strip() for s in m.content.split(".") if len(s.strip()) > 15]
        if sentences:
            snippets.append(sentences[0])

    sector_str = " + ".join(sectors)
    is_cross = cluster["cross_sector"]

    parts = []
    if is_cross:
        parts.append(f"Cross-sector insight ({sector_str}):")
    else:
        parts.append(f"{sectors[0].title()} pattern:")

    parts.append(f"{len(members)} memories converge around: {anchor.content[:100]}.")

    if snippets:
        parts.append("Threads: " + "; ".join(s[:80] for s in snippets[:3]))

    # temporal span
    timestamps = [m.created_at for m in members]
    span_days = (max(timestamps) - min(timestamps)) / 86400
    if span_days < 1:
        parts.append("Formed within a single session.")
    elif span_days < 7:
        parts.append(f"Developed over {span_days:.0f} days.")
    else:
        parts.append(f"Persistent theme spanning {span_days:.0f} days.")

    return " ".join(parts)


def calc_cluster_salience(
    cluster: Dict[str, Any],
    config: Optional[ReflectionConfig] = None
) -> float:
    """
    Salience for a reflection based on cluster properties.
    """
    cfg = config or default_config.reflection
    members = cluster["members"]
    now = time.time()

    size_score = math.log1p(len(members)) / math.log1p(10)
    anchor_weight = cluster["anchor"].meaningful_weight

    recency_sum = sum(math.exp(-(now - m.created_at) / (86400 * 7)) for m in members)
    avg_recency = recency_sum / len(members)

    cross_bonus = cfg.cross_sector_bonus if cluster["cross_sector"] else 0.0

    return min(1.0, (
        0.25 * min(1.0, size_score) +
        0.30 * anchor_weight +
        0.25 * avg_recency +
        0.20 * cross_bonus
    ))


def run_reflection(
    store: MemoryStore,
    config: Optional[ReflectionConfig] = None,
    llm_fn: Optional[Callable] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a meaningful reflection cycle.

    The system's sleep — consolidation, insight, formative detection.
    """
    cfg = config or default_config.reflection

    memories = store.get_all("active", limit=cfg.max_fetch)

    if len(memories) < cfg.min_memories:
        if verbose:
            print(f"  Only {len(memories)} memories (min {cfg.min_memories}), skipping")
        return {"created": 0, "reason": "insufficient_memories"}

    clusters = cluster_meaningful(memories, cfg)

    if verbose:
        print(f"  Found {len(clusters)} meaningful clusters")

    created = 0
    formative_marked = 0

    for cluster in clusters:
        insight_text = generate_insight(cluster, llm_fn)
        salience = calc_cluster_salience(cluster, cfg)

        # store the reflection
        reflection = store.add(
            content=insight_text,
            sector="reflective",
            tags=["reflection:meaningful"],
            metadata={
                "type": "meaningful_reflection",
                "source_ids": [m.id for m in cluster["members"]],
                "cluster_size": len(cluster["members"]),
                "cross_sector": cluster["cross_sector"],
                "sectors": list(cluster["sectors"]),
                "anchor_id": cluster["anchor"].id,
            }
        )
        reflection.salience = salience
        store.update(reflection)

        # mark source memories as consolidated
        for m in cluster["members"]:
            m.consolidated = True
            store.update(m)

        # mark anchor as formative
        cluster["anchor"].is_formative = True
        cluster["anchor"].metadata["spawned_reflections"] = \
            cluster["anchor"].metadata.get("spawned_reflections", 0) + 1
        store.update(cluster["anchor"])
        formative_marked += 1

        if verbose:
            sectors_str = ", ".join(sorted(cluster["sectors"]))
            print(f"  Created: {len(cluster['members'])} mems → [{sectors_str}] "
                  f"sal={salience:.3f}"
                  f"{' [CROSS-SECTOR]' if cluster['cross_sector'] else ''}")

        created += 1

    result = {
        "created": created,
        "clusters": len(clusters),
        "formative_marked": formative_marked,
        "cross_sector": sum(1 for c in clusters if c["cross_sector"]),
    }

    if verbose:
        print(f"  Reflection complete: {created} insights, "
              f"{formative_marked} formative marked, "
              f"{result['cross_sector']} cross-sector")

    return result
