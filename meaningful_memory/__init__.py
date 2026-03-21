"""
Meaningful Memory — Memory that knows what matters.

A standalone, framework-agnostic library for giving AI memory systems
the ability to understand significance, not just similarity.

Core modules:
    novelty     — Is this genuinely new?
    weight      — How much does this memory matter?
    decay       — Meaningful forgetting (Ebbinghaus-inspired)
    reflection  — Consolidation that creates insight
    config      — All parameters tunable in one place
    store       — Lightweight file-based memory store (no dependencies)
"""

from .config import MeaningfulConfig, default_config
from .store import MemoryStore, MemoryEntry
from .novelty import compute_novelty
from .weight import compute_weight, compute_adaptive_weight
from .decay import apply_decay, ebbinghaus_decay
from .reflection import run_reflection

__version__ = "0.1.0"
__all__ = [
    "MeaningfulConfig",
    "default_config",
    "MemoryStore",
    "MemoryEntry",
    "compute_novelty",
    "compute_weight",
    "compute_adaptive_weight",
    "apply_decay",
    "ebbinghaus_decay",
    "run_reflection",
]
