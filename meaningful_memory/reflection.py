"""
Meaningful Reflection — The system's sleep.

Consolidation that creates insight, not just compression.

Four phases:
  1. Orient  — scan the store, map clusters, assess health
  2. Signal  — score memories, identify high-value and low-value
  3. Consolidate — prune duplicates, detect contradictions, generate insights
  4. Prune & Index — move low-signal to fading, enforce limits, rebuild index

Key features:
  - Cross-sector clustering (episodic + semantic = insight)
  - Temporal clustering (memories close in time form narratives)
  - Weight-aware anchoring (important memories anchor clusters)
  - Formative detection (marks memories that spawned reflections)
"""

import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from .store import MemoryEntry, MemoryStore
from .weight import compute_weight
from .config import ReflectionConfig, MeaningfulConfig, default_config


# --- Shared utilities ---

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


# --- Phase data classes ---

@dataclass
class OrientationReport:
    """Phase 1 output: store health snapshot."""
    total_memories: int = 0
    active: int = 0
    fading: int = 0
    sectors: Dict[str, int] = field(default_factory=dict)
    cluster_count: int = 0
    avg_weight: float = 0.0


@dataclass
class SignalReport:
    """Phase 2 output: scored and ranked memories."""
    high_value_ids: List[str] = field(default_factory=list)
    low_value_ids: List[str] = field(default_factory=list)
    stale_ids: List[str] = field(default_factory=list)
    scored_count: int = 0


@dataclass
class ConsolidationReport:
    """Phase 3 output: consolidation results."""
    insights_created: int = 0
    formative_marked: int = 0
    cross_sector_insights: int = 0
    duplicates_pruned: int = 0
    contradictions_found: int = 0


@dataclass
class ReflectionReport:
    """Full four-phase reflection output."""
    orientation: OrientationReport = field(default_factory=OrientationReport)
    signal: SignalReport = field(default_factory=SignalReport)
    consolidation: ConsolidationReport = field(default_factory=ConsolidationReport)
    moved_to_fading: int = 0
    created: int = 0
    clusters: int = 0
    formative_marked: int = 0
    cross_sector: int = 0


# --- Four-phase reflection ---

def _phase_orient(
    store: MemoryStore,
    memories: List[MemoryEntry],
    config: ReflectionConfig,
    verbose: bool = False
) -> OrientationReport:
    """Phase 1: Orient — scan the store, assess health."""
    stats = store.stats()
    sectors = {}
    for m in memories:
        sectors[m.sector] = sectors.get(m.sector, 0) + 1

    weights = [m.meaningful_weight for m in memories]
    avg_weight = sum(weights) / len(weights) if weights else 0.0

    clusters = cluster_meaningful(memories, config)

    report = OrientationReport(
        total_memories=stats["total"],
        active=stats["active"],
        fading=stats["fading"],
        sectors=sectors,
        cluster_count=len(clusters),
        avg_weight=round(avg_weight, 4),
    )

    if verbose:
        print(f"  [Orient] {report.active} active, {report.fading} fading, "
              f"{report.cluster_count} clusters, avg_weight={report.avg_weight:.3f}")

    return report


def _phase_signal(
    store: MemoryStore,
    memories: List[MemoryEntry],
    config: MeaningfulConfig,
    verbose: bool = False
) -> SignalReport:
    """Phase 2: Signal — score memories, identify high/low value."""
    report = SignalReport()
    now = time.time()
    staleness_threshold = config.staleness.threshold_days * 86400

    for entry in memories:
        weight_result = compute_weight(entry, memories, config.weight)
        entry.meaningful_weight = weight_result["composite"]
        entry.recall_significance = weight_result["recall_significance"]
        entry.connectivity_weight = weight_result["connectivity"]
        store.update(entry)
        report.scored_count += 1

        if entry.meaningful_weight >= 0.6 or entry.is_formative:
            report.high_value_ids.append(entry.id)
        elif entry.meaningful_weight < 0.2 and not entry.connections and entry.access_count == 0:
            report.low_value_ids.append(entry.id)

        # staleness check
        verified = entry.verified_at or entry.created_at
        if (now - verified) > staleness_threshold:
            report.stale_ids.append(entry.id)

    if verbose:
        print(f"  [Signal] Scored {report.scored_count} memories: "
              f"{len(report.high_value_ids)} high-value, "
              f"{len(report.low_value_ids)} low-value, "
              f"{len(report.stale_ids)} stale")

    return report


def _phase_consolidate(
    store: MemoryStore,
    memories: List[MemoryEntry],
    config: MeaningfulConfig,
    llm_fn: Optional[Callable] = None,
    verbose: bool = False
) -> ConsolidationReport:
    """Phase 3: Consolidate — prune, detect contradictions, generate insights."""
    report = ConsolidationReport()

    # duplicate pruning
    from .pruning import prune_duplicates
    prune_report = prune_duplicates(store, config.pruning, verbose=verbose)
    report.duplicates_pruned = prune_report.memories_pruned

    # contradiction detection
    from .contradiction import detect_contradictions
    contradictions = detect_contradictions(store, config.contradiction, verbose=verbose)
    report.contradictions_found = len(contradictions)

    # refresh memories after pruning
    memories = store.get_all("active", limit=config.reflection.max_fetch)

    # clustering and insight generation
    clusters = cluster_meaningful(memories, config.reflection)

    for cluster in clusters:
        insight_text = generate_insight(cluster, llm_fn)
        salience = calc_cluster_salience(cluster, config.reflection)

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

        for m in cluster["members"]:
            m.consolidated = True
            store.update(m)

        cluster["anchor"].is_formative = True
        cluster["anchor"].metadata["spawned_reflections"] = \
            cluster["anchor"].metadata.get("spawned_reflections", 0) + 1
        store.update(cluster["anchor"])

        report.insights_created += 1
        report.formative_marked += 1
        if cluster["cross_sector"]:
            report.cross_sector_insights += 1

    # flag extreme-valence memories as formative candidates
    valence_flagged = 0
    for entry in store.get_all("active", limit=config.reflection.max_fetch):
        if not entry.is_formative and abs(entry.valence) > 0.7:
            entry.is_formative = True
            store.update(entry)
            valence_flagged += 1

    # regenerate wake_up.md snapshot
    top_n = getattr(config.store, "wake_up_top_n", 10)
    store.generate_wake_up(top_n=top_n)

    if verbose:
        print(f"  [Consolidate] {report.insights_created} insights, "
              f"{report.duplicates_pruned} pruned, "
              f"{report.contradictions_found} contradictions, "
              f"{valence_flagged} valence-flagged formative")

    return report


def _phase_prune_and_index(
    store: MemoryStore,
    signal_report: SignalReport,
    config: MeaningfulConfig,
    verbose: bool = False
) -> int:
    """Phase 4: Prune & Index — move low-signal to fading, enforce limits."""
    moved = 0

    for memory_id in signal_report.low_value_ids:
        entry = store.get(memory_id)
        if entry and entry.decay_state == "active":
            store.move_to_fading(memory_id)
            moved += 1

    # enforce max_active if configured
    if config.store.max_active_memories > 0:
        active = store.get_all("active", limit=config.store.max_active_memories + 100)
        if len(active) > config.store.max_active_memories:
            # sort by weight, move the lowest
            active.sort(key=lambda m: m.meaningful_weight)
            excess = len(active) - config.store.max_active_memories
            for entry in active[:excess]:
                if not entry.is_formative:
                    store.move_to_fading(entry.id)
                    moved += 1

    if verbose:
        print(f"  [Prune] Moved {moved} memories to fading")

    return moved


def run_reflection(
    store: MemoryStore,
    config: Optional[ReflectionConfig] = None,
    llm_fn: Optional[Callable] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a meaningful reflection cycle.

    Four phases: orient → signal → consolidate → prune.

    Backward compatible: accepts ReflectionConfig or uses default.
    For full four-phase behavior with all v0.3.0 features,
    use run_full_reflection() with a MeaningfulConfig.
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

        for m in cluster["members"]:
            m.consolidated = True
            store.update(m)

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


def run_full_reflection(
    store: MemoryStore,
    config: Optional[MeaningfulConfig] = None,
    llm_fn: Optional[Callable] = None,
    verbose: bool = False
) -> ReflectionReport:
    """
    Run the full four-phase reflection cycle.

    Phase 1: Orient  — scan store health
    Phase 2: Signal  — score and rank all memories
    Phase 3: Consolidate — prune, contradictions, insights
    Phase 4: Prune & Index — enforce limits, move low-value to fading

    This is the v0.3.0 reflection that combines meaning with maintenance.
    """
    cfg = config or default_config
    report = ReflectionReport()

    memories = store.get_all("active", limit=cfg.reflection.max_fetch)

    if len(memories) < cfg.reflection.min_memories:
        if verbose:
            print(f"  Only {len(memories)} memories (min {cfg.reflection.min_memories}), skipping")
        return report

    # Phase 1: Orient
    if verbose:
        print("\n  Phase 1: Orient")
    report.orientation = _phase_orient(store, memories, cfg.reflection, verbose)

    # Phase 2: Signal
    if verbose:
        print("\n  Phase 2: Signal")
    report.signal = _phase_signal(store, memories, cfg, verbose)

    # Phase 3: Consolidate
    if verbose:
        print("\n  Phase 3: Consolidate")
    report.consolidation = _phase_consolidate(store, memories, cfg, llm_fn, verbose)

    # Phase 4: Prune & Index
    if verbose:
        print("\n  Phase 4: Prune & Index")
    report.moved_to_fading = _phase_prune_and_index(store, report.signal, cfg, verbose)

    # summary fields for compatibility
    report.created = report.consolidation.insights_created
    report.formative_marked = report.consolidation.formative_marked
    report.clusters = report.orientation.cluster_count
    report.cross_sector = report.consolidation.cross_sector_insights

    if verbose:
        print(f"\n  Reflection complete: {report.created} insights, "
              f"{report.consolidation.duplicates_pruned} pruned, "
              f"{report.consolidation.contradictions_found} contradictions, "
              f"{report.moved_to_fading} moved to fading")

    return report
