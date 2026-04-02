"""
Duplicate Pruning — Consolidate without losing meaning.

Detects near-duplicate memories and merges them, preserving
the richest metadata on the surviving anchor. Pruned entries
are moved to pruned/ (never hard-deleted).

Key principles:
  1. Highest-weighted version becomes the anchor
  2. Connections, tags, and access history are merged
  3. If any duplicate is formative, the survivor is formative
  4. Pruned entries persist in pruned/ for auditability
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .store import MemoryEntry, MemoryStore
from .config import PruningConfig, default_config


@dataclass
class PruneReport:
    """Results of a pruning operation."""
    groups_found: int = 0
    memories_pruned: int = 0
    anchors: List[str] = field(default_factory=list)
    pruned_ids: List[str] = field(default_factory=list)


def token_similarity(a: MemoryEntry, b: MemoryEntry) -> float:
    """Jaccard similarity between two memories' token sets."""
    ta, tb = a.tokens, b.tokens
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_duplicate_groups(
    memories: List[MemoryEntry],
    similarity_threshold: float = 0.85
) -> List[List[MemoryEntry]]:
    """
    Find groups of near-duplicate memories.

    Returns list of groups, each sorted by meaningful_weight descending
    (first element is the best anchor candidate).
    """
    used = set()
    groups = []

    # sort by weight so highest-weight memories anchor groups
    sorted_mems = sorted(memories, key=lambda m: m.meaningful_weight, reverse=True)

    for mem in sorted_mems:
        if mem.id in used:
            continue

        group = [mem]
        used.add(mem.id)

        for candidate in sorted_mems:
            if candidate.id in used:
                continue
            if token_similarity(mem, candidate) >= similarity_threshold:
                group.append(candidate)
                used.add(candidate.id)

        if len(group) >= 2:
            groups.append(group)

    return groups


def merge_into_anchor(anchor: MemoryEntry, duplicates: List[MemoryEntry]) -> MemoryEntry:
    """
    Fold metadata from duplicates into the anchor.

    Merges connections, tags, and access history.
    If any duplicate is formative, anchor becomes formative.
    """
    all_connections = set(anchor.connections)
    all_tags = set(anchor.tags)
    all_history = list(anchor.access_history)

    for dup in duplicates:
        all_connections.update(dup.connections)
        all_tags.update(dup.tags)
        all_history.extend(dup.access_history)
        anchor.access_count += dup.access_count

        if dup.is_formative:
            anchor.is_formative = True

        if dup.meaningful_weight > anchor.meaningful_weight:
            anchor.meaningful_weight = dup.meaningful_weight

    # remove self-references
    all_connections.discard(anchor.id)
    for dup in duplicates:
        all_connections.discard(dup.id)

    anchor.connections = sorted(all_connections)
    anchor.tags = sorted(all_tags)
    anchor.access_history = sorted(all_history)

    anchor.metadata["pruned_count"] = anchor.metadata.get("pruned_count", 0) + len(duplicates)
    anchor.metadata["pruned_ids"] = anchor.metadata.get("pruned_ids", []) + [d.id for d in duplicates]

    return anchor


def prune_duplicates(
    store: MemoryStore,
    config: Optional[PruningConfig] = None,
    dry_run: bool = False,
    verbose: bool = False
) -> PruneReport:
    """
    Find and merge near-duplicate memories.

    Pruned entries are moved to pruned/ — never deleted.
    """
    cfg = config or default_config.pruning
    report = PruneReport()

    memories = store.get_all("active", limit=500)
    groups = find_duplicate_groups(memories, cfg.similarity_threshold)
    report.groups_found = len(groups)

    if verbose:
        print(f"  Found {len(groups)} duplicate groups")

    for group in groups:
        anchor = group[0]
        duplicates = group[1:]

        if verbose:
            print(f"  Anchor [{anchor.id[:8]}]: \"{anchor.content[:50]}...\"")
            for dup in duplicates:
                sim = token_similarity(anchor, dup)
                print(f"    Duplicate [{dup.id[:8]}] sim={sim:.3f}: \"{dup.content[:50]}...\"")

        if not dry_run:
            merge_into_anchor(anchor, duplicates)
            store.update(anchor)

            for dup in duplicates:
                store.move_to_pruned(dup.id)
                report.pruned_ids.append(dup.id)

        report.anchors.append(anchor.id)
        report.memories_pruned += len(duplicates)

    if verbose:
        print(f"  Pruning complete: {report.memories_pruned} duplicates merged into {len(report.anchors)} anchors")

    return report
