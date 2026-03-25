# meaningful-memory

**Memory that knows what matters.**

A zero-dependency Python library for giving AI memory systems the ability to understand *significance*, not just similarity. Works standalone or as a layer on top of any memory framework.

```
pip install meaningful-memory
```

## The Problem

Current AI memory systems store everything the same way. A debugging session and a conversation that changes how you think get the same weight, the same decay rate, the same retrieval priority. There's no concept of *significance*.

Human memory doesn't work this way. It encodes with emotion, strengthens through spaced recall, connects across domains, and lets unimportant things fade. We need the AI equivalent.

## See It Work

```bash
python examples/demo.py
```

Zero dependencies. Zero API keys. Instant visual proof of the difference between flat memory and meaningful memory.

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
from meaningful_memory import run_reflection

# The system's "sleep" — finds cross-cutting insights
results = run_reflection(store, verbose=True)
# → "Cross-sector insight (episodic + semantic + reflective):
#     5 memories converge on consciousness as emergent phenomenon..."
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

### File-Based Store

```python
from meaningful_memory import MemoryStore

store = MemoryStore("./memories")

# Human-readable YAML+Markdown files
entry = store.add(
    content="the pronoun shift reveals unconscious framing",
    sector="reflective",
    tags=["consciousness", "language"]
)

# Search, connect, retrieve
results = store.search("consciousness")
store.connect(entry_a.id, entry_b.id)
stats = store.stats()
```

Memories stored as individual `.md` files with YAML frontmatter. No database. Runs on a Raspberry Pi.

## Full Pipeline

```python
from meaningful_memory import (
    MemoryStore, compute_novelty, compute_weight,
    apply_decay, run_reflection, compute_resonance
)

store = MemoryStore("./memories")

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

# 5. Run reflection (find cross-cutting insights)
run_reflection(store, verbose=True)

# 6. Check for resonance (the meta-signal)
profile = compute_resonance(entry, store.get_all())
if profile.is_resonant:
    print(f"Resonant memory detected: {profile.resonance_class}")
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
```

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

Open source because memory systems are infrastructure for the future. They belong to everyone.

## License

MIT
