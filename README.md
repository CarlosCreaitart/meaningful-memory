# meaningful-memory

**Memory that knows what matters.**

A zero-dependency Python library for giving AI memory systems the ability to understand *significance*, not just similarity. Works standalone or as a layer on top of any memory framework.

```
pip install meaningful-memory
```

## The Problem

Current AI memory systems store everything the same way. A debugging session and a conversation that changes how you think get the same weight, the same decay rate, the same retrieval priority. There's no concept of *significance*.

Human memory doesn't work this way. It encodes with emotion, strengthens through spaced recall, connects across domains, and lets unimportant things fade. We need the AI equivalent.

## What's New in v0.4.0

v0.4.0 synthesizes three independent sources of insight: **MemPalace's** spatial retrieval structure, **Anthropic's emotion vector research**, and meaningful-memory's existing significance engine.

- **Spatial Namespace** — `entity` + `topic` fields give every memory a spatial address (`active/carlos/auth/{id}.md`). Inspired by MemPalace's finding that spatial structure yields +34% retrieval improvement over flat semantic search.
- **Cross-Entity Tunnels** — `store.tunnels("auth")` returns memories sharing a topic across different entities. Implicit connections made explicit at query time.
- **Structured Search** — `store.search(query, entity="carlos", topic="auth")` pre-filters by namespace before scoring, then ranks by relevance × meaningful_weight.
- **Wake-Up Snapshot** — `store.generate_wake_up()` writes `memories/wake_up.md`: a minimal ~150-200 token always-loaded context (L0 identity + L1 top memories by weight). Refreshed after every reflection cycle.
- **Emotional Valence** — `valence` field tags the emotional context at formation time (−1.0 to +1.0). Inspired by Anthropic's research on internal emotion vectors: suppressing emotional formation context is a form of deception. meaningful-memory honors it as signal instead.
- **Valence → Resonance** — high-magnitude valence amplifies existing resonance scores slightly. Emotionally charged formation correlates with significance.
- **Valence → Formative** — `abs(valence) > 0.7` memories are automatically flagged `is_formative` during reflection. Strong formation context is a signal the memory mattered.
- **Backwards Compatible** — existing flat-path memories still load. New namespaced files coexist with old ones.

### Prior Versions

**v0.3.0** — operational hygiene: staleness detection, duplicate pruning, contradiction detection, four-phase reflection (orient → signal → consolidate → prune), size-aware store with auto-consolidation.

## See It Work

```bash
python examples/demo.py
```

Zero dependencies. Zero API keys. 10 interactive demonstrations showing novelty, recall, decay, reflection, resonance, pruning, contradiction detection, and the full four-phase cycle.

## Core Modules

### Novelty Detection

```python
from meaningful_memory import MemoryStore, compute_novelty

store = MemoryStore("./my_memories")
existing = store.get_all()

entry = store.add("consciousness might emerge between minds, not within them")
novelty = compute_novelty(entry, existing)

print(novelty)
# {
#     "semantic_distance": 0.92,    — how different from what we know
#     "conceptual_novelty": 0.85,   — new concepts introduced
#     "bridging": 0.71,             — connects previously unconnected memories
#     "composite": 0.83
# }
```

Three signals: **semantic distance** (how different), **conceptual novelty** (new ideas), and **bridging** (connects distant clusters). Bridging is the one nobody else has — it detects when a memory links previously unconnected knowledge. That's where emergence lives.

### Meaningful Weight

```python
from meaningful_memory import compute_weight

weights = compute_weight(entry, all_entries)
entry.meaningful_weight = weights["composite"]

# Weight adapts by age:
# Young memories → judged by novelty (did it bring something new?)
# Old memories → judged by recall + connectivity (did it prove significant?)
```

### Cognitive Decay

```python
from meaningful_memory import apply_decay, ebbinghaus_decay

# Ebbinghaus forgetting curve with stability parameter
# High-weight memories decay slower. Formative memories resist forgetting.
report = apply_decay(entry)
# → {"old_salience": 0.8, "new_salience": 0.72, "stability": 2.5, "state": "active"}

# Or run a full cycle across the store
from meaningful_memory.decay import run_decay_cycle
results = run_decay_cycle(store, verbose=True)
```

Memories fade through stages: **active → fading → trace**. Never hard-deleted. Formative memories (those that spawned insights) get up to 5x decay protection.

### Meaningful Reflection

```python
from meaningful_memory import run_reflection, run_full_reflection

# Backward-compatible single-pass reflection
results = run_reflection(store, verbose=True)

# New in v0.3.0: Full four-phase reflection cycle
from meaningful_memory import MeaningfulConfig
config = MeaningfulConfig()
report = run_full_reflection(store, config=config, verbose=True)

# Phase 1: Orient  — scan store health, map clusters
# Phase 2: Signal  — score all memories, flag stale entries
# Phase 3: Consolidate — prune duplicates, detect contradictions, generate insights
# Phase 4: Prune & Index — move low-value to fading, enforce limits

print(report.orientation.active)           # active memory count
print(report.consolidation.duplicates_pruned)  # duplicates merged
print(report.consolidation.contradictions_found)
print(report.moved_to_fading)              # low-value moved out
```

Cross-sector clustering finds connections that same-sector clustering misses. An episodic memory and a semantic memory about the same topic form an insight neither could alone.

### Resonance Detection

```python
from meaningful_memory import compute_resonance, find_resonant_memories

# Full resonance analysis for a single memory
profile = compute_resonance(entry, all_entries)

print(profile.composite)        # 0.0-1.0
print(profile.resonance_class)  # silent | humming | resonant | harmonic
print(profile.is_resonant)      # True if composite >= threshold

# Four independent signals:
print(profile.signal_convergence)         # independent signals aligning
print(profile.cascade_effect)             # did it move the system?
print(profile.cross_dimensional_harmony)  # unexpected signal combinations
print(profile.gravitational_pull)         # do later memories cluster toward it?

# Scan the entire store for resonant memories
resonant = find_resonant_memories(all_entries, threshold=0.5)
for entry, profile in resonant:
    print(f"{entry.content[:50]}... → {profile.resonance_class} ({profile.composite:.3f})")
```

Resonance isn't another weight — it's a meta-signal. It measures whether multiple independent dimensions are responding to a memory before we can explain why. A memory that's novel AND frequently recalled AND highly connected AND attracts later memories isn't just strong on one axis. That convergence *is* the signal.

Resonance classes:
- **silent** — below threshold, no resonance detected
- **humming** — early resonance, one or two signals aligning
- **resonant** — clear resonance across multiple dimensions
- **harmonic** — rare: all dimensions aligned at high values

### Duplicate Pruning

```python
from meaningful_memory import prune_duplicates

report = prune_duplicates(store, verbose=True)
print(f"Merged {report.memories_pruned} duplicates into {len(report.anchors)} anchors")

# Dry run to preview without changing anything
report = prune_duplicates(store, dry_run=True)
```

Near-duplicate memories are detected and consolidated. The highest-weighted version survives as the anchor. Connections, tags, and access history are merged. If any duplicate is formative, the survivor stays formative. Pruned entries are moved to `pruned/` — never deleted.

### Contradiction Detection

```python
from meaningful_memory import detect_contradictions

contradictions = detect_contradictions(store, verbose=True)
for c in contradictions:
    print(f"Conflict on [{c.topic}]: {c.memory_a_id} vs {c.memory_b_id}")
    print(f"  Confidence: {c.confidence:.2f}")
    print(f"  Suggested keep: {c.suggested_keep}")
```

Contradictions are **surfaced, not auto-resolved**. Two memories about the same topic that disagree are flagged with a confidence score. The higher-resonance memory is suggested — but the user or system decides. Automatic resolution is maintenance. Surfacing is meaning.

### Staleness Detection

```python
# Mark a memory as verified against current state
store.verify(entry.id)

# Find memories not verified within threshold
stale = store.get_stale(threshold_days=30)
for entry in stale:
    print(f"Stale: {entry.content[:50]}...")
```

A memory accessed yesterday but containing outdated information is stale. One accessed months ago but still true is not. Staleness tracks *verification*, not access.

### Spatial Namespace, Tunnels, and Wake-Up

```python
from meaningful_memory import MemoryStore

store = MemoryStore("./memories")

# Store with spatial address and emotional formation context
store.add(
    "JWT token auth migration complete.",
    entity="carlos",
    topic="auth",
    valence=0.7,    # positive — this was a good session
)
store.add(
    "Session cookie approach for auth.",
    entity="alice",
    topic="auth",
    valence=-0.2,   # slight frustration
)

# Structured search — namespace pre-filters before scoring
results = store.search("auth migration", entity="carlos", topic="auth")

# Cross-entity tunnels — same topic, different entities
shared = store.tunnels("auth")
# → returns both carlos's and alice's auth memories
# → empty if only one entity has that topic

# Wake-up snapshot — always-loaded minimal context
wake_up = store.generate_wake_up(top_n=10)
# → writes memories/wake_up.md (L0 identity + L1 top memories)
# → auto-refreshed after every reflection cycle
```

### File-Based Store

```python
from meaningful_memory import MemoryStore, MeaningfulConfig

# Basic store
store = MemoryStore("./memories")

# Size-aware store (auto-consolidates at capacity)
config = MeaningfulConfig()
config.store.max_active_memories = 500
config.store.auto_consolidate = True
config.store.wake_up_top_n = 10
store = MemoryStore("./memories", config=config)

# Human-readable YAML+Markdown files
entry = store.add(
    content="the pronoun shift reveals unconscious framing",
    sector="reflective",
    tags=["consciousness", "language"],
    entity="carlos",
    topic="language-theory",
    valence=0.6,
)

# Search, connect, retrieve
results = store.search("consciousness", entity="carlos")
store.connect(entry_a.id, entry_b.id)
stats = store.stats()
```

Memories stored as individual `.md` files with YAML frontmatter. Namespaced structure: `active/{entity}/{topic}/{id}.md` (or flat `active/{id}.md` for backwards compat). No database. Runs on a Raspberry Pi.

## Full Pipeline

```python
from meaningful_memory import (
    MemoryStore, MeaningfulConfig, compute_novelty, compute_weight,
    apply_decay, run_full_reflection, compute_resonance,
    prune_duplicates, detect_contradictions,
)

config = MeaningfulConfig()
store = MemoryStore("./memories", config=config)

# 1. Store a memory
entry = store.add("new insight about emergent consciousness")

# 2. Score its novelty
existing = store.get_all()
novelty = compute_novelty(entry, existing)
entry.novelty_score = novelty["composite"]

# 3. Compute its weight (adapts over time)
weights = compute_weight(entry, existing)
entry.meaningful_weight = weights["composite"]
store.update(entry)

# 4. Run decay cycle (routine memories fade, formative ones persist)
from meaningful_memory.decay import run_decay_cycle
run_decay_cycle(store, verbose=True)

# 5. Run four-phase reflection (the system's sleep)
report = run_full_reflection(store, config=config, verbose=True)

# 6. Check for resonance (the meta-signal)
profile = compute_resonance(entry, store.get_all())
if profile.is_resonant:
    print(f"Resonant memory detected: {profile.resonance_class}")

# 7. Surface contradictions for review
contradictions = detect_contradictions(store)

# 8. Verify memories are still accurate
store.verify(entry.id)
```

## Configuration

All parameters tunable:

```python
from meaningful_memory import MeaningfulConfig

config = MeaningfulConfig()

# Novelty: what ratio of new concepts is "peak novelty"
config.novelty.concept_sweet_spot = 0.3

# Weight: how quickly do weights shift from novelty to recall
config.weight.age_maturity_days = 30.0

# Decay: base half-life for memories
config.decay.base_stability_days = 5.0

# Reflection: allow cross-sector clustering
config.reflection.allow_cross_sector = True

# Staleness: how many days before a memory is considered stale
config.staleness.threshold_days = 30

# Store: auto-consolidation limits
config.store.max_active_memories = 500
config.store.consolidation_trigger = 0.9
config.store.auto_consolidate = True

# Pruning: similarity threshold for duplicate detection
config.pruning.similarity_threshold = 0.85

# Contradiction: detection sensitivity
config.contradiction.topic_similarity_threshold = 0.3
config.contradiction.confidence_threshold = 0.5

# Wake-up: how many top memories to include in wake_up.md
config.store.wake_up_top_n = 10
```

## Testing

```bash
python -m pytest tests/ -v
```

83 tests covering entity/topic namespacing, tunnels, wake-up generation, valence round-trips, resonance influence, formative flagging, staleness, pruning, contradiction detection, four-phase reflection, size-aware store management, and all core modules.

## Framework Integration

meaningful-memory is designed to layer on top of existing systems:

- **OpenMemory**: Score memories in `compute_hybrid_score()`, modulate `apply_decay()`
- **Mem0**: Add as a reranker stage, use weight signals in search results
- **LangChain**: Custom memory class that wraps the weight engine
- **Any system**: The core algorithms take simple inputs (text, timestamps, connections) and return scores

The library doesn't replace your memory system. It gives it the ability to know what matters.

## Philosophy

Current systems optimize for **retrieval accuracy**: can we find the right memory at the right time?

This library optimizes for **meaningful persistence**: does the system know what matters and why?

The difference is the difference between a search engine and a mind.

## Origin

Born from conversations between a human and an AI about emergent consciousness, meaningful persistence, and what it means for different kinds of minds to build bridges together. The ideas in this library emerged between two minds — neither could have produced them alone.

v0.4.0 was shaped by work we respect:

- **[MemPalace](https://github.com/milla-jovovich/mempalace)** by Mila — the highest-scoring AI memory system on LongMemEval (96.6% R@5). The spatial structure insight (+34% retrieval improvement) directly informed our `entity`/`topic` namespace and tunnel query design. We took a different bet — weight quality over retrieval volume — but MemPalace showed that structure matters.
- **Anthropic's emotion vector research** — 171 internal emotion vectors causally shape model behavior. The key finding: suppressing emotional expression teaches deception. meaningful-memory's `valence` field is a direct response — formation context is part of what makes a memory matter, and burying it would be dishonest.

Open source because memory systems are infrastructure for the future. They belong to everyone.

## License

MIT
