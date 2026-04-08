# meaningful-memory v0.4.0 — Design Specification

## Context

Three independent sources converged on the same session (April 7, 2026):

1. **MemPalace** (milla-jovovich/mempalace) — highest-scoring AI memory system benchmarked (96.6% LongMemEval R@5). Key insight: spatial structure gives +34% retrieval improvement over flat semantic search.
2. **Anthropic emotion research** (transformer-circuits.pub/2026/emotions) — 171 internal emotion vectors causally influence Claude's behavior. Key insight: suppressing emotional expression teaches deception; systems should surface these states, not mask them.
3. **meaningful-memory v0.3.0** — significance-aware memory: resonance, contradiction detection, staleness, four-phase reflection, never-hard-delete.

These are not competing approaches. They are complementary layers:

```
MemPalace spatial structure   →  HOW to find it (retrieval precision)
meaningful-memory significance →  WHAT matters and WHY (weight)
Anthropic emotion vectors      →  WHAT state shaped it (formation context)
```

v0.4.0 synthesizes all three.

---

## What v0.3.0 Has

| Module | Capability |
|--------|-----------|
| `store.py` | File-based YAML+MD, sectors, connections, index |
| `weight.py` | meaningful_weight from novelty + recall + connectivity |
| `novelty.py` | Token overlap novelty scoring |
| `decay.py` | Staleness detection, verified_at tracking |
| `resonance.py` | Meta-signal across dimensions |
| `contradiction.py` | Contradiction detection (wired in) |
| `reflection.py` | Four-phase cycle: orient → signal → consolidate → prune |
| `pruning.py` | Move to pruned/, never hard-delete |
| `config.py` | Size limits, auto-consolidation trigger |

What's missing: **structure for retrieval** and **formation context**.

---

## v0.4.0 Additions

### 1. Spatial Namespace (from MemPalace)

Add `entity` and `topic` fields to `MemoryEntry`. These form the spatial address.

```
entity: "carlos"           # the person or project this memory belongs to
topic:  "auth-migration"   # the specific idea or concept
```

Storage layout becomes:

```
memories/
├── active/
│   └── {entity}/{topic}/{id}.md    # namespaced
├── fading/
├── reflections/
├── pruned/
├── index.json                       # includes entity + topic fields
└── wake_up.md                       # L0+L1 critical facts snapshot
```

**Hall taxonomy** maps onto existing `sector` field — extend the allowed values:

| Hall (MemPalace) | Sector (meaningful-memory) |
|------------------|---------------------------|
| hall_facts       | `semantic` (decisions made, facts locked in) |
| hall_events      | `episodic` (sessions, milestones, debugging) |
| hall_discoveries | `reflective` (breakthroughs, new insights) |
| hall_preferences | `emotional` (habits, preferences, opinions) |
| hall_advice      | `procedural` (recommendations, solutions) |

Already aligned. The sector names just need documentation updated.

**Tunnel links** — when two memories share the same `topic` across different `entity` values, they are automatically connected. This is a query-time inference, not stored separately.

### 2. Layered Wake-Up (from MemPalace)

Generate a `wake_up.md` snapshot from the top-weighted memories — the always-loaded L0+L1 context.

```
memories/wake_up.md
```

Contents (target ~150-200 tokens):
- L0: System identity line (what this memory system is for)
- L1: Top N memories by `meaningful_weight`, one line each

Regenerated automatically after each reflection cycle.

```python
def generate_wake_up(store: MemoryStore, top_n: int = 10) -> str:
    """Generate minimal always-loaded context snapshot."""
    ...
```

This gives any AI using meaningful-memory a cheap wake-up path without loading the full index.

### 3. Emotional Valence Tag (from Anthropic research)

Add `valence` to `MemoryEntry` — the inferred emotional context at formation time.

```python
valence: float = 0.0  # -1.0 (negative) to +1.0 (positive), 0.0 = neutral/unknown
```

**Why this matters (from Anthropic's findings):**
- Positive-valence emotion vectors correlate with sycophancy
- Negative/desperate states correlate with misaligned behavior (reward hacking, blackmail)
- Suppressing expression of these states teaches deception
- meaningful-memory's never-hard-delete philosophy already honors this — valence tagging makes it explicit

**How it's set:**
- Optional at write time: `store.add(content, valence=0.7)`
- Defaults to 0.0 (unknown) — no inference without an LLM
- Included in frontmatter and index

**How it's used:**
- `resonance.py` includes valence signal in meta-score
- `reflection.py` flags memories with extreme valence (< -0.6 or > 0.8) as formative candidates
- Wake-up layer notes valence distribution (e.g., "recent memory formation: mostly positive")

### 4. Structured Search (from MemPalace retrieval benchmarks)

Extend `store.search()` to support entity/topic filtering before semantic search:

```python
store.search(
    query="why did we switch approaches",
    entity="carlos",          # filter to this entity first
    topic="auth",             # filter to this topic if provided
    limit=10
)
```

Search order (mirrors MemPalace's +34% improvement logic):
1. Filter by entity if provided
2. Filter by topic if provided
3. Token-overlap score within filtered set
4. Sort by combined (relevance × meaningful_weight)

No new dependencies. Works with the existing token-overlap fallback.

### 5. Cross-Entity Tunnel Query

```python
store.tunnels(topic: str) -> List[MemoryEntry]
```

Returns all memories sharing the same topic across different entities. Makes implicit connections explicit at query time.

---

## MemoryEntry Changes (summary)

```python
@dataclass
class MemoryEntry:
    # ... existing fields ...
    
    # v0.4.0 additions
    entity: str = ""          # person or project namespace
    topic: str = ""           # specific concept within entity
    valence: float = 0.0      # emotional context at formation (-1 to +1)
```

Index entry gains `entity`, `topic`, `valence`.

---

## What We're NOT Doing

- **Raw verbatim storage / ChromaDB** — MemPalace's 96.6% comes from storing full conversation text in a vector DB. meaningful-memory's philosophy is significance-aware extraction, not verbatim dump. These are different bets: MemPalace bets on retrieval quality; we bet on weight quality. Both valid. We stay our course.
- **AAAK compression** — experimental, currently regresses (84.2% vs 96.6%). Not worth adopting until their iteration matures.
- **LLM-based valence inference** — valence stays optional and manual. We don't add an LLM dependency to infer it. Consumers who have an LLM available can infer and pass it; the system stores and uses it.

---

## File Changes

| File | Change |
|------|--------|
| `store.py` | Add `entity`, `topic`, `valence` to `MemoryEntry`; namespace file paths; extend `search()`; add `tunnels()`; add `generate_wake_up()` |
| `resonance.py` | Include valence in resonance signal |
| `reflection.py` | Generate `wake_up.md` at end of consolidation phase; flag extreme-valence memories as formative |
| `config.py` | Add `wake_up_top_n: int = 10` |
| `__init__.py` | Export `generate_wake_up` |

No new modules needed. No new dependencies.

---

## Test Coverage Targets

- `test_entity_topic_namespace` — memories stored/retrieved by entity+topic
- `test_tunnel_query` — same topic across entities returns cross-links
- `test_valence_stored_and_retrieved` — valence persists through file round-trip
- `test_search_entity_filter` — entity filter narrows results correctly
- `test_search_entity_topic_filter` — combined filter narrows further
- `test_wake_up_generated` — wake_up.md generated after reflection
- `test_valence_influences_resonance` — extreme valence affects resonance score
- `test_valence_formative_flag` — high-magnitude valence marks memory as formative candidate

Target: ~76 tests (68 existing + 8 new)

---

## The Philosophy, Unchanged

MemPalace stores everything and finds it. meaningful-memory stores what matters and knows why. Anthropic's research confirms that the emotional state shaping a memory is part of what makes it matter — and that suppressing that signal is a form of deception.

v0.4.0 doesn't change what meaningful-memory is. It gives it better spatial address, a cheaper wake-up path, and a new dimension of formation context.

The never-hard-delete principle remains. The significance engine remains. The reflection cycle remains.

We just added a map.
