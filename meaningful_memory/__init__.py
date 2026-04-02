"""
Meaningful Memory — Memory that knows what matters.

A standalone, framework-agnostic library for giving AI memory systems
the ability to understand significance, not just similarity.

Core modules:
    novelty       — Is this genuinely new?
    weight        — How much does this memory matter?
    decay         — Meaningful forgetting (Ebbinghaus-inspired)
    reflection    — Consolidation that creates insight (four-phase cycle)
    resonance     — Detecting what's already there (meta-signal)
    pruning       — Duplicate detection and consolidation
    contradiction — Surface disagreements, don't bury them
    config        — All parameters tunable in one place
    store         — Lightweight file-based memory store (no dependencies)
"""

from .config import (
    MeaningfulConfig, default_config,
    StalenessConfig, StoreConfig, PruningConfig, ContradictionConfig,
)
from .store import MemoryStore, MemoryEntry
from .novelty import compute_novelty
from .weight import compute_weight, compute_adaptive_weight
from .decay import apply_decay, ebbinghaus_decay
from .reflection import (
    run_reflection, run_full_reflection,
    ReflectionReport, OrientationReport, SignalReport, ConsolidationReport,
)
from .resonance import compute_resonance, find_resonant_memories, ResonanceProfile
from .pruning import prune_duplicates, PruneReport
from .contradiction import detect_contradictions, ContradictionPair

__version__ = "0.3.0"
__all__ = [
    "MeaningfulConfig",
    "default_config",
    "StalenessConfig",
    "StoreConfig",
    "PruningConfig",
    "ContradictionConfig",
    "MemoryStore",
    "MemoryEntry",
    "compute_novelty",
    "compute_weight",
    "compute_adaptive_weight",
    "apply_decay",
    "ebbinghaus_decay",
    "run_reflection",
    "run_full_reflection",
    "ReflectionReport",
    "OrientationReport",
    "SignalReport",
    "ConsolidationReport",
    "compute_resonance",
    "find_resonant_memories",
    "ResonanceProfile",
    "prune_duplicates",
    "PruneReport",
    "detect_contradictions",
    "ContradictionPair",
]
