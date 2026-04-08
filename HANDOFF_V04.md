# meaningful-memory v0.4.0 — Build Handoff

## What This Is

A build handoff for the next session to implement v0.4.0. Read `V04_DESIGN.md` first for full context and rationale. This doc is the implementation checklist.

## Context in One Paragraph

Three sources converged: MemPalace (spatial structure = +34% retrieval), Anthropic's emotion vector research (formation context matters, suppressing it = deception), and meaningful-memory v0.3.0 (significance-aware, never-hard-delete, 68 tests). v0.4.0 synthesizes them. No new dependencies. No philosophy changes. We're adding a map, a wake-up layer, and an emotional formation tag.

## Current State

- Version: `0.3.0` (`pyproject.toml`)
- Tests: 68, all passing
- Core module: `meaningful_memory/store.py` — `MemoryEntry` dataclass + `MemoryStore` class
- Design doc: `V04_DESIGN.md` — full spec, read it

## Build Plan

### Step 1 — Extend `MemoryEntry` in `store.py`

Add three fields to the dataclass:

```python
entity: str = ""      # person or project namespace (e.g. "carlos", "meaningful-memory")
topic: str = ""       # specific concept (e.g. "auth", "resonance", "book-outline")
valence: float = 0.0  # emotional context at formation: -1.0 (negative) to +1.0 (positive)
```

Update `to_file_content()` and `from_file_content()` to serialize/deserialize these fields.

Update index entries to include `entity`, `topic`, `valence`.

### Step 2 — Namespace file paths

Change storage from flat `active/{id}.md` to namespaced:

```
active/{entity}/{id}.md       # if entity set, no topic
active/{entity}/{topic}/{id}.md  # if both set
active/{id}.md                # fallback if neither set (backwards compatible)
```

Update `add()`, `move_to_fading()`, `move_to_pruned()`, `_rebuild_index()` to handle the new paths. Keep backwards compatibility — old flat files still load.

### Step 3 — Extend `search()` in `store.py`

```python
def search(self, query: str, entity: str = "", topic: str = "", limit: int = 10) -> List[MemoryEntry]:
```

Filter order before token-overlap scoring:
1. If `entity` provided → only search memories where `entry.entity == entity`
2. If `topic` provided → further filter where `entry.topic == topic`
3. Token-overlap score within filtered set
4. Sort by `(relevance_score × meaningful_weight)` — weight matters, not just match

### Step 4 — Add `tunnels()` to `MemoryStore`

```python
def tunnels(self, topic: str) -> List[MemoryEntry]:
    """Return all memories sharing a topic across different entities."""
    results = []
    seen_entities = set()
    for entry in self.get_all("active", limit=500):
        if entry.topic == topic and entry.entity:
            results.append(entry)
            seen_entities.add(entry.entity)
    # Only return if topic appears in more than one entity
    if len(seen_entities) <= 1:
        return []
    return results
```

### Step 5 — Add `generate_wake_up()` to `store.py`

```python
def generate_wake_up(self, top_n: int = 10) -> str:
    """Generate minimal always-loaded context snapshot (~150-200 tokens)."""
```

Logic:
- Get all active memories sorted by `meaningful_weight` descending
- Take top `top_n`
- Format as compact markdown: one line per memory with weight, entity, topic, and first 100 chars of content
- Prepend an L0 identity line
- Write to `memories/wake_up.md`
- Return the content

### Step 6 — Update `resonance.py`

Include `valence` in the resonance signal. High-magnitude valence (abs > 0.6) boosts resonance score slightly — emotionally charged formation context is a signal that the memory matters.

```python
valence_signal = abs(entry.valence) * 0.1  # small weight, not dominant
```

### Step 7 — Update `reflection.py`

At the end of the consolidation phase:
1. Call `store.generate_wake_up()` to refresh `wake_up.md`
2. Flag memories with `abs(valence) > 0.7` as `is_formative = True` if not already set

### Step 8 — Update `config.py`

Add to store config:
```python
wake_up_top_n: int = 10
```

### Step 9 — Update `__init__.py`

Export `generate_wake_up` at package level.

### Step 10 — Update `pyproject.toml`

Bump version: `0.3.0` → `0.4.0`

---

## Tests to Write

Target: ~76 total (68 existing + 8 new). Add to `tests/` — follow existing test file conventions.

| Test | What it checks |
|------|---------------|
| `test_entity_topic_stored` | Memory with entity+topic round-trips through file correctly |
| `test_namespace_path` | Files stored in correct subdirectory when entity/topic set |
| `test_backwards_compat` | Old flat-path memories still load after namespace change |
| `test_search_entity_filter` | entity filter narrows results to matching entity only |
| `test_search_entity_topic_filter` | combined entity+topic filter narrows further |
| `test_tunnel_query` | Same topic across two entities → tunnels() returns both; single entity → returns [] |
| `test_wake_up_generated` | wake_up.md created after generate_wake_up(), contains top memories |
| `test_valence_resonance` | High-magnitude valence increases resonance score vs neutral |
| `test_valence_formative` | abs(valence) > 0.7 → is_formative flagged during reflection |

---

## What NOT to Change

- Never-hard-delete philosophy — `move_to_pruned()` stays, no actual deletion added
- Zero-dependency constraint — no ChromaDB, no embeddings, no LLM calls in core
- Existing 68 tests must still pass
- `sector` field — don't rename it, the hall taxonomy maps onto it conceptually but the field name stays
- `meaningful_weight` calculation — untouched, valence is additive to resonance only

---

## Key Files

```
meaningful_memory/store.py        ← primary changes (Steps 1-5, 9)
meaningful_memory/resonance.py    ← Step 6
meaningful_memory/reflection.py   ← Step 7
meaningful_memory/config.py       ← Step 8
meaningful_memory/__init__.py     ← Step 9
pyproject.toml                    ← Step 10
V04_DESIGN.md                     ← full rationale, read first
tests/                            ← add 8-9 new tests
```

---

## Done When

- All 76+ tests pass
- `wake_up.md` generates after reflection
- `store.search(entity="x", topic="y")` narrows correctly
- `store.tunnels("auth")` returns cross-entity memories or empty list
- Old flat-path memories still load (backwards compat)
- Version bumped to `0.4.0`
