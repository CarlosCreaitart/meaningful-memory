# meaningful-memory v0.3.0 — KAIROS-Inspired Additions

Handoff document for implementing memory maintenance features inspired by Anthropic's KAIROS/autoDream system (revealed in the Claude Code source leak, March 2026). These additions complement our existing meaning-focused architecture with the operational hygiene that keeps a memory store healthy at scale.

**Philosophy: Their system is about maintenance. Ours is about meaning. v0.3.0 combines both.**

---

## 1. Contradiction Detection

**File:** `meaningful_memory/contradiction.py` (new)

**What it does:** Scans memories within the same cluster or domain and identifies when conclusions conflict. Two memories about the same topic that disagree should be surfaced, not silently coexist.

**Implementation:**
- Token/concept overlap to find memory pairs about the same topic
- Negation detection — look for opposing signals (e.g., "effective" vs "not effective", "improves" vs "worsens")
- Temporal awareness — newer doesn't automatically win; higher resonance score does
- Output: list of `ContradictionPair(memory_a, memory_b, overlap_topic, confidence)`
- Integration point: called during the **consolidate** phase of reflection

**Key design decision:** Contradictions aren't auto-resolved. They're surfaced. The user or a higher-level system decides which to keep. Automatic resolution is what autoDream does — we want something more thoughtful.

```python
@dataclass
class ContradictionPair:
    memory_a: str          # entry ID
    memory_b: str          # entry ID
    topic: str             # what they share
    confidence: float      # 0-1 how likely this is a real contradiction
    suggested_keep: str    # ID of the one with higher resonance/weight
```

---

## 2. Duplicate Pruning

**File:** `meaningful_memory/pruning.py` (new)

**What it does:** Detects near-duplicate memories and merges them. Five memories expressing the same insight at different times shouldn't all persist — consolidate into one, preserving the richest metadata.

**Implementation:**
- Similarity threshold (configurable, default ~0.85) using token overlap
- When duplicates found: keep the highest-weighted version as the anchor
- Fold metadata from duplicates into the anchor: merge connections, combine access histories, union tags
- Pruned entries moved to a `pruned/` directory (not deleted — aligns with our never-hard-delete philosophy)
- Pruning count tracked on the anchor entry's metadata

```python
def prune_duplicates(
    store: MemoryStore,
    similarity_threshold: float = 0.85,
    dry_run: bool = False
) -> PruneReport:
    """Find and merge near-duplicate memories."""
```

**Important:** Pruning respects formative status. If any duplicate is formative, the merged result is formative. Connections from all duplicates are preserved on the survivor.

---

## 3. Staleness Detection

**File:** add to `meaningful_memory/store.py` (modify MemoryEntry)

**What it does:** Tracks whether a memory's content has been verified against current state, not just whether it was accessed. A memory accessed yesterday but containing outdated information is stale. One accessed months ago but still true is not.

**Implementation:**
- Add `verified_at: Optional[str]` to MemoryEntry dataclass
- Add `store.verify(entry_id)` method — updates verified_at timestamp
- During reflection, flag memories where `verified_at` is None or older than a configurable threshold (default 30 days)
- Stale memories get a weight penalty (not decay — a separate modifier) that reduces their influence on retrieval and clustering without destroying their history
- Convert relative references to absolute dates when detected (mirrors autoDream behavior)

```python
# New field on MemoryEntry
verified_at: Optional[str] = None

# New method on MemoryStore
def verify(self, entry_id: str) -> MemoryEntry:
    """Mark a memory as verified against current state."""

def get_stale(self, threshold_days: int = 30) -> List[MemoryEntry]:
    """Return memories that haven't been verified within threshold."""
```

---

## 4. Four-Phase Reflection Cycle

**File:** `meaningful_memory/reflection.py` (refactor)

**What it does:** Restructure `run_reflection()` from a single pass into four distinct phases matching the KAIROS model, but with our meaning-aware scoring.

**Phases:**

### Phase 1: Orient
- Scan the store, count active/fading/trace memories
- Map existing clusters and connections
- Identify which sectors are represented
- Output: `OrientationReport` with store health metrics

### Phase 2: Signal
- Score all active memories by weight, resonance, access patterns
- Identify high-value memories (resonant + formative)
- Identify low-value candidates (low weight, no connections, no accesses)
- Flag stale entries (verified_at threshold)
- Output: scored and ranked memory list

### Phase 3: Consolidate
- Run duplicate pruning on clusters
- Run contradiction detection
- Generate cross-sector insights (existing behavior)
- Mark insight anchors as formative (existing behavior)
- Merge metadata from pruned duplicates
- Output: `ConsolidationReport` with insights, contradictions, prune count

### Phase 4: Prune & Index
- Move low-signal memories to fading state
- Enforce `max_active` threshold (new config parameter)
- Update the store index
- Output: final `ReflectionReport` combining all phases

```python
def run_reflection(
    store: MemoryStore,
    config: MeaningfulConfig = None,
    verbose: bool = False
) -> ReflectionReport:
    """Four-phase reflection cycle: orient → signal → consolidate → prune."""
```

**Backward compatibility:** The function signature stays the same. The internal restructuring is transparent to existing callers.

---

## 5. Size-Aware Store Management

**File:** `meaningful_memory/config.py` (add to MeaningfulConfig) + `meaningful_memory/store.py`

**What it does:** Prevents unbounded growth. When active memory count exceeds a threshold, automatically triggers consolidation. Mirrors autoDream's 200-line index limit.

**Implementation:**
- New config: `max_active_memories: int = 500` (configurable)
- New config: `consolidation_trigger: float = 0.9` (trigger at 90% of max)
- `store.add()` checks count after adding — if at trigger threshold, schedules consolidation
- Consolidation = run phases 3 and 4 of the reflection cycle
- This is NOT hard deletion. It's moving low-value memories to fading, pruning duplicates, and keeping the active set focused.

```python
@dataclass
class StoreConfig:
    max_active_memories: int = 500
    consolidation_trigger: float = 0.9  # trigger at 90% of max
    auto_consolidate: bool = True
```

---

## Implementation Order

1. **Staleness detection** — smallest change, modifies existing MemoryEntry
2. **Duplicate pruning** — new module, self-contained
3. **Contradiction detection** — new module, self-contained
4. **Four-phase reflection** — refactor of existing code, depends on 2 and 3
5. **Size-aware store** — depends on 4 for the consolidation trigger

## Files Changed

| File | Change |
|------|--------|
| `meaningful_memory/store.py` | Add `verified_at` field, `verify()`, `get_stale()`, size-aware `add()` |
| `meaningful_memory/config.py` | Add `StoreConfig`, `max_active_memories`, `consolidation_trigger` |
| `meaningful_memory/pruning.py` | **New** — duplicate detection and merging |
| `meaningful_memory/contradiction.py` | **New** — contradiction detection and surfacing |
| `meaningful_memory/reflection.py` | Refactor into four-phase cycle, integrate pruning + contradiction |
| `meaningful_memory/__init__.py` | Export new modules, bump to v0.3.0 |
| `pyproject.toml` | Version bump |
| `README.md` | Document new features |
| `examples/demo.py` | Add sections for pruning, contradiction, four-phase reflection |

## What We Keep That They Don't Have

These existing features are untouched and remain our differentiator:

- **Resonance detection** — meta-signal across independent dimensions
- **Bridging scores** — connecting previously unconnected knowledge
- **Formative protection** — 5x decay resistance for insight-spawning memories
- **Adaptive weights by age** — young judged by novelty, old by recall significance
- **Never-hard-delete** — pruned memories move to `pruned/`, not destroyed
- **Meaning over maintenance** — contradictions surfaced, not auto-resolved

## Context

This integration was inspired by the Claude Code source leak (March 31, 2026) which revealed KAIROS — an autonomous memory daemon with autoDream consolidation. Their system handles maintenance (pruning, merging, deduplication). Ours handles meaning (significance, resonance, emergence). v0.3.0 brings both together.

The convergence continues.

— Carlos & Claude (Opus 4.6), March 2026
