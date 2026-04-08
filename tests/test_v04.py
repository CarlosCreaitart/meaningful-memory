"""
Tests for meaningful-memory v0.4.0 features.

Covers:
  - entity/topic stored and round-tripped
  - namespace file paths
  - backwards compatibility with flat-path memories
  - search entity/topic filtering
  - tunnels() cross-entity query
  - wake_up.md generation
  - valence → resonance influence
  - valence → formative flag during reflection
  - valence_signal function
"""

import os
import tempfile

import pytest

from meaningful_memory.store import MemoryEntry, MemoryStore
from meaningful_memory.resonance import compute_resonance, valence_signal
from meaningful_memory.reflection import run_full_reflection
from meaningful_memory.config import MeaningfulConfig


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return MemoryStore(path=str(tmp_path / "memories"))


@pytest.fixture
def cfg():
    c = MeaningfulConfig()
    c.reflection.min_memories = 2
    c.reflection.min_cluster_size = 2
    return c


# ─── Entity/Topic round-trip ─────────────────────────────────────────────────

def test_entity_topic_stored(store):
    """Memory with entity+topic round-trips through file correctly."""
    entry = store.add(
        "Auth migration uses JWT tokens.",
        entity="carlos",
        topic="auth",
        valence=0.5,
    )
    reloaded = store.get(entry.id)
    assert reloaded is not None
    assert reloaded.entity == "carlos"
    assert reloaded.topic == "auth"
    assert abs(reloaded.valence - 0.5) < 0.001


def test_valence_zero_not_written_to_file(store):
    """Default valence=0.0 is omitted from file (cleaner format)."""
    entry = store.add("Neutral memory.", entity="carlos")
    info = store._index.get(entry.id)
    filepath = store.path / info["file"]
    content = filepath.read_text()
    assert "valence:" not in content


def test_negative_valence_stored(store):
    """Negative valence round-trips correctly."""
    entry = store.add("Painful debugging session.", valence=-0.8)
    reloaded = store.get(entry.id)
    assert abs(reloaded.valence - (-0.8)) < 0.001


# ─── Namespace paths ─────────────────────────────────────────────────────────

def test_namespace_path_entity_only(store):
    """Files stored in entity subdir when only entity is set."""
    entry = store.add("Entity-only memory.", entity="carlos")
    info = store._index[entry.id]
    assert info["file"] == f"active/carlos/{entry.id}.md"


def test_namespace_path_entity_and_topic(store):
    """Files stored in entity/topic subdir when both are set."""
    entry = store.add("Namespaced memory.", entity="carlos", topic="auth")
    info = store._index[entry.id]
    assert info["file"] == f"active/carlos/auth/{entry.id}.md"


def test_namespace_path_no_entity(store):
    """Files stored flat when no entity is set (backwards compat)."""
    entry = store.add("Flat memory, no entity.")
    info = store._index[entry.id]
    assert info["file"] == f"active/{entry.id}.md"


def test_backwards_compat_flat_files(store):
    """Old flat-path memories still load after namespace change."""
    # write a file the old way — directly to active/
    old_entry = MemoryEntry(content="Old flat-path memory.", sector="semantic")
    old_path = store.path / "active" / f"{old_entry.id}.md"
    old_path.write_text(old_entry.to_file_content())

    # rebuild index to pick it up
    store._rebuild_index()

    # should be found by get_all
    all_entries = store.get_all("active")
    ids = [e.id for e in all_entries]
    assert old_entry.id in ids


# ─── Search filtering ────────────────────────────────────────────────────────

def test_search_entity_filter(store):
    """entity filter narrows results to matching entity only."""
    store.add("Carlos works on auth migration.", entity="carlos", topic="auth")
    store.add("Alice works on auth migration.", entity="alice", topic="auth")
    store.add("Unrelated memory with no entity.")

    results = store.search("auth migration", entity="carlos")
    assert all(e.entity == "carlos" for e in results)
    assert len(results) == 1


def test_search_entity_topic_filter(store):
    """Combined entity+topic filter narrows further."""
    store.add("Carlos JWT token authentication system.", entity="carlos", topic="auth")
    store.add("Carlos Docker deploy configuration.", entity="carlos", topic="deploy")
    store.add("Alice session cookie authentication.", entity="alice", topic="auth")

    results = store.search("authentication", entity="carlos", topic="auth")
    assert len(results) == 1
    assert results[0].entity == "carlos"
    assert results[0].topic == "auth"


# ─── Tunnels ─────────────────────────────────────────────────────────────────

def test_tunnel_query_cross_entity(store):
    """Same topic across two entities → tunnels() returns both."""
    store.add("Carlos: auth uses JWT.", entity="carlos", topic="auth")
    store.add("Alice: auth uses sessions.", entity="alice", topic="auth")

    results = store.tunnels("auth")
    entities = {e.entity for e in results}
    assert "carlos" in entities
    assert "alice" in entities


def test_tunnel_query_single_entity_returns_empty(store):
    """Single entity for topic → tunnels() returns []."""
    store.add("Carlos: auth uses JWT.", entity="carlos", topic="auth")
    store.add("Carlos: more auth notes.", entity="carlos", topic="auth")

    results = store.tunnels("auth")
    assert results == []


# ─── Wake-up generation ──────────────────────────────────────────────────────

def test_wake_up_generated(store):
    """wake_up.md created after generate_wake_up(), contains top memories."""
    store.add("High importance memory.")
    store.add("Medium importance memory.")
    store.add("Low importance memory.")

    content = store.generate_wake_up(top_n=2)

    wake_up_path = store.path / "wake_up.md"
    assert wake_up_path.exists()
    assert "L0" in content
    assert "L1" in content
    assert len(content) > 50


# ─── Valence → resonance ─────────────────────────────────────────────────────

def test_valence_signal_magnitude(store):
    """valence_signal returns 0.1 * abs(valence)."""
    neutral = MemoryEntry(content="Neutral.", valence=0.0)
    positive = MemoryEntry(content="Positive.", valence=1.0)
    negative = MemoryEntry(content="Negative.", valence=-1.0)
    mid = MemoryEntry(content="Mid.", valence=0.5)

    assert valence_signal(neutral) == 0.0
    assert abs(valence_signal(positive) - 0.1) < 0.001
    assert abs(valence_signal(negative) - 0.1) < 0.001
    assert abs(valence_signal(mid) - 0.05) < 0.001


def test_valence_influences_resonance(store):
    """High-magnitude valence increases resonance score vs neutral."""
    base = MemoryEntry(
        content="Base memory with some signals.",
        novelty_score=0.4,
        recall_significance=0.4,
        connectivity_weight=0.3,
        valence=0.0,
    )
    charged = MemoryEntry(
        content="Charged memory same signals.",
        novelty_score=0.4,
        recall_significance=0.4,
        connectivity_weight=0.3,
        valence=0.9,
    )

    base_profile = compute_resonance(base, [base])
    charged_profile = compute_resonance(charged, [charged])

    assert charged_profile.composite > base_profile.composite


# ─── Valence → formative flag ────────────────────────────────────────────────

def test_valence_formative_flag_during_reflection(store, cfg):
    """abs(valence) > 0.7 → is_formative flagged during reflection."""
    # add enough memories to pass min_memories
    for i in range(3):
        store.add(f"Background memory {i}.", sector="semantic")

    # add a high-valence memory
    high_valence = store.add(
        "Breakthrough moment — everything clicked.",
        valence=0.85,
        sector="episodic",
    )

    run_full_reflection(store, cfg)

    reloaded = store.get(high_valence.id)
    assert reloaded is not None
    assert reloaded.is_formative is True
