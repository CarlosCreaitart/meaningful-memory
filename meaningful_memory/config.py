"""
Configuration for Meaningful Memory.

All tunable parameters in one place. Override defaults by passing
a MeaningfulConfig instance to any module function, or modify
the default_config singleton.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class NoveltyConfig:
    """Controls how novelty is measured."""
    top_k_neighbors: int = 5
    concept_sweet_spot: float = 0.3
    bridge_threshold: float = 0.4
    max_bridge_pairs: int = 10
    weights: Dict[str, float] = field(default_factory=lambda: {
        "semantic_distance": 0.35,
        "conceptual_novelty": 0.30,
        "bridging": 0.35,
    })


@dataclass
class WeightConfig:
    """Controls how meaningful weight is calculated."""
    age_maturity_days: float = 30.0
    young_weights: Dict[str, float] = field(default_factory=lambda: {
        "novelty": 0.50,
        "recall": 0.20,
        "connectivity": 0.30,
    })
    mature_weights: Dict[str, float] = field(default_factory=lambda: {
        "novelty": 0.15,
        "recall": 0.40,
        "connectivity": 0.45,
    })
    gap_resilience_scale_days: float = 7.0
    frequency_cap: int = 50
    recency_halflife_days: float = 30.0


@dataclass
class DecayConfig:
    """Controls cognitive decay behavior."""
    base_stability_days: float = 5.0
    trace_floor_ratio: float = 0.05
    fading_threshold: float = 0.15
    trace_threshold: float = 0.08
    max_formative_protection: float = 5.0
    decay_ceiling: float = 1.5
    decay_weight_factor: float = 1.3
    min_lambda: float = 0.001
    max_lambda: float = 0.1
    sample_ratio: float = 0.1


@dataclass
class ReflectionConfig:
    """Controls meaningful reflection behavior."""
    min_memories: int = 10
    max_fetch: int = 200
    semantic_threshold: float = 0.6
    temporal_window_hours: float = 24.0
    allow_cross_sector: bool = True
    min_cluster_size: int = 2
    max_cluster_size: int = 8
    cross_sector_bonus: float = 0.2


@dataclass
class MeaningfulConfig:
    """Master configuration for all modules."""
    novelty: NoveltyConfig = field(default_factory=NoveltyConfig)
    weight: WeightConfig = field(default_factory=WeightConfig)
    decay: DecayConfig = field(default_factory=DecayConfig)
    reflection: ReflectionConfig = field(default_factory=ReflectionConfig)
    enabled: bool = True
    verbose: bool = False


default_config = MeaningfulConfig()
