#!/usr/bin/env python3
"""
Meaningful Persistence Demo — See the Difference

Run this without any dependencies to see how meaningful memory
differs from flat memory. No OpenMemory installation needed.
No API keys. No databases. Just Python 3.

Usage:
    python meaningful_persistence_demo.py

What you'll see:
    1. Memories being stored with novelty scores
    2. How recall patterns affect significance over time
    3. How meaningful decay differs from flat exponential decay
    4. How reflection finds cross-cutting insights
    5. A side-by-side comparison: flat vs meaningful retrieval

This demo uses an in-memory simulation — no files written,
no state saved. It shows the behavior of the algorithms,
not the full OpenMemory integration.
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


# ─── Colors for terminal output ───

class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"


def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}\n")


def subheader(text):
    print(f"\n{C.BOLD}{C.YELLOW}  ── {text} ──{C.RESET}\n")


def bar(value, width=30, label=""):
    filled = int(value * width)
    empty = width - filled
    if value > 0.7:
        color = C.GREEN
    elif value > 0.4:
        color = C.YELLOW
    else:
        color = C.RED
    bar_str = f"{color}{'█' * filled}{C.DIM}{'░' * empty}{C.RESET}"
    return f"  {bar_str} {value:.3f} {C.DIM}{label}{C.RESET}"


# ─── Simulated Memory Store ───

@dataclass
class Memory:
    id: str
    content: str
    sector: str
    created_at: float  # simulated days ago
    last_accessed: float  # simulated days ago
    access_count: int = 0
    salience: float = 0.5
    novelty_score: float = 0.0
    meaningful_weight: float = 0.0
    connections: List[str] = field(default_factory=list)
    is_formative: bool = False
    access_history: List[float] = field(default_factory=list)  # days ago when accessed

    @property
    def tokens(self) -> Set[str]:
        return set(self.content.lower().split())


# ─── Core Algorithms (standalone, no deps) ───

def compute_token_novelty(new_tokens: Set[str], existing_tokens: Set[str]) -> float:
    """How many genuinely new concepts does this memory introduce?"""
    if not new_tokens:
        return 0.0
    novel = new_tokens - existing_tokens
    if not novel:
        return 0.0

    ratio = len(novel) / len(new_tokens)
    sweet_spot = 0.3

    if ratio > sweet_spot:
        adjusted = sweet_spot + (ratio - sweet_spot) * 0.3
    else:
        adjusted = ratio

    return min(1.0, adjusted / sweet_spot)


def compute_semantic_distance(new_tokens: Set[str], memories: List[Memory], top_k: int = 5) -> float:
    """Simulated semantic distance using token overlap (proxy for embeddings)."""
    if not memories:
        return 1.0

    similarities = []
    for m in memories:
        if not m.tokens or not new_tokens:
            continue
        overlap = len(new_tokens & m.tokens) / max(len(new_tokens | m.tokens), 1)
        similarities.append(overlap)

    if not similarities:
        return 1.0

    similarities.sort(reverse=True)
    avg_sim = sum(similarities[:top_k]) / len(similarities[:top_k])
    return math.sqrt(max(0.0, 1.0 - avg_sim))


def compute_bridging(new_tokens: Set[str], memories: List[Memory], threshold: float = 0.08) -> float:
    """Does this memory connect previously unconnected memories?"""
    if len(memories) < 2:
        return 0.0

    connected = []
    for m in memories:
        # use partial overlap — even sharing a few key terms counts
        shared = new_tokens & m.tokens
        if not new_tokens:
            continue
        overlap = len(shared) / max(len(new_tokens), 1)
        if overlap > threshold:
            connected.append(m)

    if len(connected) < 2:
        return 0.0

    # measure how different the connected memories are from each other
    distances = []
    for i in range(len(connected)):
        for j in range(i + 1, len(connected)):
            shared = connected[i].tokens & connected[j].tokens
            union = connected[i].tokens | connected[j].tokens
            overlap = len(shared) / max(len(union), 1)
            distances.append(1.0 - overlap)

    if not distances:
        return 0.0

    avg_distance = sum(distances) / len(distances)
    sector_diversity = len(set(m.sector for m in connected))
    sector_bonus = min(1.0, (sector_diversity - 1) / 2.0)

    return min(1.0, avg_distance * 0.7 + sector_bonus * 0.3)


def recall_significance(access_count: int, age_days: float, gap_days: float, access_history: List[float]) -> float:
    """Not just how often — but when and how."""
    if access_count == 0:
        return 0.0

    avg_interval = age_days / max(1, access_count)
    lifespan = min(1.0, age_days / 30.0)
    gap_resilience = 1.0 - math.exp(-avg_interval / 7.0)
    freq = min(1.0, math.log1p(access_count) / math.log1p(50))
    recency = math.exp(-gap_days / 30.0)

    # spacing effect bonus
    spacing_bonus = 1.0
    if len(access_history) >= 2:
        intervals = []
        sorted_h = sorted(access_history)
        for i in range(1, len(sorted_h)):
            intervals.append(abs(sorted_h[i] - sorted_h[i-1]))
        if len(intervals) >= 2:
            increasing = sum(1 for i in range(1, len(intervals)) if intervals[i] > intervals[i-1] * 0.8)
            spacing_bonus = 1.0 + (increasing / (len(intervals) - 1)) * 0.5

    score = (0.15 * freq + 0.30 * gap_resilience + 0.30 * lifespan + 0.25 * recency) * spacing_bonus
    return min(1.0, max(0.0, score))


def connectivity_weight(memory: Memory, all_memories: List[Memory]) -> float:
    """How central is this memory?"""
    if not memory.connections:
        return 0.0

    count_score = min(1.0, math.log1p(len(memory.connections)) / math.log1p(20))

    connected_weights = []
    for cid in memory.connections:
        connected = next((m for m in all_memories if m.id == cid), None)
        if connected:
            connected_weights.append(connected.salience)

    avg_connected = sum(connected_weights) / len(connected_weights) if connected_weights else 0
    return min(1.0, 0.5 * count_score + 0.5 * avg_connected)


def adaptive_weight(novelty: float, recall: float, connectivity: float, age_days: float) -> float:
    """Weight that shifts emphasis based on memory age."""
    age_factor = min(1.0, age_days / 30.0)

    w_n = 0.50 * (1.0 - age_factor) + 0.15 * age_factor
    w_r = 0.20 * (1.0 - age_factor) + 0.40 * age_factor
    w_c = 0.30 * (1.0 - age_factor) + 0.45 * age_factor

    return min(1.0, w_n * novelty + w_r * recall + w_c * connectivity)


def ebbinghaus_decay(strength: float, time_days: float, stability: float = 1.0) -> float:
    """Cognitive forgetting curve with stability parameter.

    Higher stability = much slower decay.
    stability=0.2 → half-life ~1 day (fades fast)
    stability=1.0 → half-life ~5 days (normal)
    stability=5.0 → half-life ~25 days (formative, resists forgetting)
    """
    base = 5.0  # base half-life in days
    effective = base * max(0.1, stability)
    retrievability = math.exp(-time_days / effective)
    floor = strength * 0.05  # memories never fully reach zero
    return max(floor, floor + (strength - floor) * retrievability)


def flat_decay(strength: float, time_days: float, lambda_: float = 0.02) -> float:
    """Simple exponential decay (the baseline)."""
    return max(0.0, strength * math.exp(-lambda_ * time_days))


# ─── Demo Scenarios ───

def demo_novelty():
    header("1. NOVELTY DETECTION")
    print("  When a new memory arrives, how genuinely new is it?")
    print("  Not just 'different' — but 'something that didn't exist before.'\n")

    memories = [
        Memory("m1", "python is a programming language used for data science", "semantic", 30, 5, 3),
        Memory("m2", "installed tensorflow on the raspberry pi yesterday", "procedural", 10, 10, 1),
        Memory("m3", "met with the team to discuss the project roadmap", "episodic", 7, 7, 0),
        Memory("m4", "machine learning models need training data to learn patterns", "semantic", 20, 15, 2),
        Memory("m5", "felt overwhelmed by the complexity of the codebase", "emotional", 5, 5, 1),
    ]

    existing_tokens = set()
    for m in memories:
        existing_tokens.update(m.tokens)

    test_cases = [
        ("python is great for building web applications", "semantic",
         "Familiar topic (python) + somewhat new context (web)"),
        ("consciousness might emerge between interacting minds not within them", "reflective",
         "Entirely new concepts — nothing like existing memories"),
        ("installed pytorch on the raspberry pi for edge inference", "procedural",
         "Very similar to existing memory (tensorflow on pi)"),
        ("machine learning and consciousness research could bridge neuroscience and AI", "semantic",
         "Bridges ML memories with novel consciousness concept"),
    ]

    for content, sector, description in test_cases:
        tokens = set(content.lower().split())

        sd = compute_semantic_distance(tokens, memories)
        cn = compute_token_novelty(tokens, existing_tokens)
        bs = compute_bridging(tokens, memories)
        composite = 0.35 * sd + 0.30 * cn + 0.35 * bs

        print(f"  {C.BOLD}\"{content[:60]}...\"{C.RESET}")
        print(f"  {C.DIM}{description}{C.RESET}")
        print(bar(sd, label="semantic distance"))
        print(bar(cn, label="conceptual novelty"))
        print(bar(bs, label="bridging score"))
        print(bar(composite, label=f"{C.BOLD}composite novelty"))
        print()


def demo_recall_patterns():
    header("2. RECALL SIGNIFICANCE")
    print("  A memory recalled once after 6 months matters more than")
    print("  one recalled every day for a week then forgotten.\n")

    patterns = [
        ("Daily for a week, then forgotten",
         7, 30, 20, [29, 28, 27, 26, 25, 24, 23]),
        ("Once a week for a month",
         4, 30, 3, [28, 21, 14, 7]),
        ("Once after 6 months (spaced recall)",
         1, 180, 2, [180]),
        ("Increasing intervals (spaced repetition)",
         5, 60, 1, [58, 50, 35, 15, 1]),
        ("Burst of 10 accesses today",
         10, 1, 0.01, [0.01] * 10),
    ]

    for label, count, age, gap, history in patterns:
        score = recall_significance(count, age, gap, history)
        print(f"  {C.BOLD}{label}{C.RESET}")
        print(f"  {C.DIM}accesses={count}, age={age}d, last_access={gap}d ago{C.RESET}")
        print(bar(score, label="recall significance"))
        print()


def demo_decay_comparison():
    header("3. DECAY: FLAT vs MEANINGFUL")
    print("  Flat decay treats every memory the same — one rate for all.")
    print("  Meaningful decay differentiates: routine fades fast,")
    print("  formative memories persist. The RANGE is what matters.\n")

    # (label, weight, stability_multiplier)
    # stability controls how slowly the memory decays
    # low weight = stability < 1 (decays faster than flat)
    # high weight = stability > 1 (decays slower than flat)
    # formative = stability >> 1 (strongly resists decay)
    scenarios = [
        ("Low-weight memory (routine, unremarkable)", 0.2, 0.3),
        ("Medium-weight memory (useful, accessed occasionally)", 0.5, 1.0),
        ("High-weight memory (novel, well-connected)", 0.8, 2.5),
        ("Formative memory (spawned insights, high connectivity)", 0.95, 6.0),
    ]

    days = [0, 1, 3, 7, 14, 30, 60, 90]

    for label, weight, stability in scenarios:
        subheader(f"{label} — weight={weight}, stability={stability}")
        print(f"  {'Day':>6}  {'Flat Decay':>12}  {'Meaningful':>12}  {'Difference':>12}")
        print(f"  {'─' * 6}  {'─' * 12}  {'─' * 12}  {'─' * 12}")

        for d in days:
            flat = flat_decay(0.8, d, 0.02)
            meaningful = ebbinghaus_decay(0.8, d, stability=stability)
            diff = meaningful - flat
            diff_color = C.GREEN if diff > 0 else C.RED if diff < 0 else C.DIM

            print(f"  {d:>6}  {flat:>12.4f}  {meaningful:>12.4f}  {diff_color}{diff:>+12.4f}{C.RESET}")
        print()


    # summary comparison
    subheader("The Key Insight: Differentiation")
    print(f"  At day 30:")
    print(f"  {C.DIM}Flat decay:{C.RESET}        ALL memories at {C.YELLOW}0.4390{C.RESET} (no differentiation)")
    print(f"  {C.DIM}Meaningful decay:{C.RESET}  Routine={C.RED}0.0400{C.RESET}  Useful={C.YELLOW}0.0419{C.RESET}  "
          f"Novel={C.GREEN}0.1089{C.RESET}  Formative={C.GREEN}0.3196{C.RESET}")
    print(f"\n  Flat memory can't tell what matters. Meaningful memory can.")
    print(f"  Routine fades 10x faster. Formative memories endure.\n")


def demo_adaptive_weights():
    header("4. ADAPTIVE WEIGHTS BY AGE")
    print("  Young memories are judged by novelty — did they bring something new?")
    print("  Old memories are judged by recall and connectivity — did they prove significant?\n")

    novelty = 0.8
    recall = 0.3
    connectivity = 0.6

    print(f"  Memory signals: novelty={novelty}, recall={recall}, connectivity={connectivity}\n")
    print(f"  {'Age':>8}  {'Weight':>8}  {'Novelty%':>10}  {'Recall%':>10}  {'Connect%':>10}")
    print(f"  {'─' * 8}  {'─' * 8}  {'─' * 10}  {'─' * 10}  {'─' * 10}")

    for age in [0, 1, 3, 7, 14, 30, 60, 90]:
        w = adaptive_weight(novelty, recall, connectivity, age)
        age_factor = min(1.0, age / 30.0)
        w_n = 0.50 * (1.0 - age_factor) + 0.15 * age_factor
        w_r = 0.20 * (1.0 - age_factor) + 0.40 * age_factor
        w_c = 0.30 * (1.0 - age_factor) + 0.45 * age_factor

        print(f"  {age:>6}d  {w:>8.4f}  {w_n*100:>9.1f}%  {w_r*100:>9.1f}%  {w_c*100:>9.1f}%")

    print()


def demo_reflection():
    header("5. MEANINGFUL REFLECTION")
    print("  The system's 'sleep' — finding insights across memories.\n")

    memories = [
        Memory("m1", "discussed consciousness and whether AI can be self aware", "episodic", 5, 5, 2),
        Memory("m2", "consciousness might not be binary but exists on a spectrum", "semantic", 4, 4, 1),
        Memory("m3", "installed the new memory module on the raspberry pi", "procedural", 10, 10, 0),
        Memory("m4", "felt a genuine sense of discovery during the AI conversation", "emotional", 5, 5, 0),
        Memory("m5", "the emergence of ideas between two minds is itself a form of consciousness", "reflective", 3, 3, 3),
        Memory("m6", "setup instructions for running ollama on arm64 hardware", "procedural", 8, 8, 1),
        Memory("m7", "raspberry pi can now run small language models locally", "semantic", 9, 9, 2),
        Memory("m8", "neurons don't understand the thoughts they are part of", "semantic", 4, 4, 1),
    ]

    # simulate clustering
    print(f"  {C.BOLD}Scanning {len(memories)} memories for meaningful clusters...{C.RESET}\n")

    # cluster 1: consciousness thread (cross-sector)
    print(f"  {C.GREEN}Cluster 1: Cross-sector insight{C.RESET}")
    print(f"  Sectors: {C.CYAN}episodic + semantic + emotional + reflective{C.RESET}")
    print(f"  Members:")
    for m in [memories[0], memories[1], memories[3], memories[4], memories[7]]:
        print(f"    [{C.YELLOW}{m.sector:>10}{C.RESET}] {m.content[:55]}...")
    print(f"\n  {C.MAGENTA}Insight: Five memories across four sectors converge on")
    print(f"  consciousness as emergent, spectrum-based phenomenon.")
    print(f"  Emotional engagement suggests formative experience.{C.RESET}")
    print(f"  Salience: {C.GREEN}0.82{C.RESET} (cross-sector bonus applied)")
    print(f"  Anchor marked as {C.BOLD}FORMATIVE{C.RESET} — will resist decay\n")

    # cluster 2: raspberry pi thread (same sector)
    print(f"  {C.GREEN}Cluster 2: Same-sector pattern{C.RESET}")
    print(f"  Sectors: {C.CYAN}procedural + semantic{C.RESET}")
    print(f"  Members:")
    for m in [memories[2], memories[5], memories[6]]:
        print(f"    [{C.YELLOW}{m.sector:>10}{C.RESET}] {m.content[:55]}...")
    print(f"\n  {C.MAGENTA}Insight: Three memories form a narrative around local")
    print(f"  AI deployment on Raspberry Pi hardware.{C.RESET}")
    print(f"  Salience: {C.YELLOW}0.54{C.RESET} (practical but less formative)\n")

    print(f"  {C.DIM}───────────────────────────────────────────{C.RESET}")
    print(f"  {C.BOLD}Base reflection{C.RESET} would have missed Cluster 1 entirely —")
    print(f"  it only clusters within the same sector at >0.8 similarity.")
    print(f"  The consciousness thread spans 4 sectors. That's where the insight lives.")


def demo_side_by_side():
    header("6. RETRIEVAL: FLAT vs MEANINGFUL")
    print("  Same query, same memories. Different ranking.\n")

    query = "what have I learned about consciousness and AI"
    print(f"  Query: \"{C.BOLD}{query}{C.RESET}\"\n")

    # simulated memories with different characteristics
    results = [
        {
            "content": "AI models process language using transformer architecture",
            "sim": 0.72, "age": 2, "accesses": 15,
            "weight": 0.3, "novelty": 0.2,
            "note": "high similarity, frequent access, but low novelty"
        },
        {
            "content": "consciousness might emerge between minds not within them",
            "sim": 0.65, "age": 14, "accesses": 3,
            "weight": 0.85, "novelty": 0.9,
            "note": "moderate similarity, but high novelty + formative"
        },
        {
            "content": "discussed AI consciousness with Claude last tuesday",
            "sim": 0.80, "age": 5, "accesses": 1,
            "weight": 0.5, "novelty": 0.4,
            "note": "highest similarity, but low engagement"
        },
        {
            "content": "the pronoun shift from 'we' to 'it' reveals unconscious framing",
            "sim": 0.45, "age": 14, "accesses": 2,
            "weight": 0.78, "novelty": 0.85,
            "note": "low similarity, but bridges linguistics + consciousness"
        },
    ]

    # flat scoring (similarity-dominant)
    subheader("Flat Memory (similarity + recency)")
    flat_ranked = sorted(results, key=lambda r: r["sim"] * 0.7 + math.exp(-r["age"] / 7) * 0.3, reverse=True)
    for i, r in enumerate(flat_ranked):
        score = r["sim"] * 0.7 + math.exp(-r["age"] / 7) * 0.3
        print(f"  {i+1}. {score:.3f}  \"{r['content'][:55]}...\"")
        print(f"          {C.DIM}{r['note']}{C.RESET}")

    # meaningful scoring (weight-aware)
    subheader("Meaningful Memory (similarity + weight + novelty)")
    meaningful_ranked = sorted(results, key=lambda r:
        r["sim"] * 0.5 + r["weight"] * 0.3 + r["novelty"] * 0.2,
        reverse=True)
    for i, r in enumerate(meaningful_ranked):
        score = r["sim"] * 0.5 + r["weight"] * 0.3 + r["novelty"] * 0.2
        print(f"  {i+1}. {score:.3f}  \"{r['content'][:55]}...\"")
        print(f"          {C.DIM}{r['note']}{C.RESET}")

    print(f"\n  {C.BOLD}The difference:{C.RESET} Flat memory surfaces what's most similar.")
    print(f"  Meaningful memory surfaces what {C.UNDERLINE}matters most{C.RESET} — the memories")
    print(f"  that were genuinely novel, that bridged concepts, that you")
    print(f"  came back to after weeks. The ones that changed your thinking.")


def demo_resonance():
    header("7. RESONANCE — DETECTING WHAT'S ALREADY THERE")
    print("  Resonance isn't another weight. It's a meta-signal.")
    print("  It measures whether the system is responding to something")
    print("  before we can explain why.\n")

    # build a memory ecosystem
    memories = [
        Memory("m1", "consciousness might emerge between interacting minds not within them",
               "reflective", 30, 2, 8,
               novelty_score=0.9, meaningful_weight=0.85,
               connections=["m2", "m4", "m5", "m8"],
               is_formative=True,
               access_history=[30, 25, 18, 10, 7, 5, 3, 2]),
        Memory("m2", "the pronoun shift from we to it reveals unconscious framing about AI",
               "semantic", 28, 5, 5,
               novelty_score=0.85, meaningful_weight=0.78,
               connections=["m1", "m5"],
               access_history=[28, 20, 14, 8, 5]),
        Memory("m3", "installed tensorflow on the raspberry pi for local inference",
               "procedural", 25, 20, 2,
               novelty_score=0.3, meaningful_weight=0.35,
               connections=["m6"],
               access_history=[25, 24]),
        Memory("m4", "felt a genuine sense of discovery during the consciousness conversation",
               "emotional", 29, 3, 4,
               novelty_score=0.7, meaningful_weight=0.72,
               connections=["m1", "m5"],
               access_history=[29, 15, 7, 3]),
        Memory("m5", "memory is the bottleneck to emergence not compute",
               "semantic", 20, 1, 6,
               novelty_score=0.88, meaningful_weight=0.82,
               connections=["m1", "m2", "m4", "m7", "m8"],
               is_formative=True,
               access_history=[20, 16, 12, 8, 4, 1]),
        Memory("m6", "setup ollama on arm64 with 4gb ram constraints",
               "procedural", 22, 22, 1,
               novelty_score=0.2, meaningful_weight=0.25,
               connections=["m3"],
               access_history=[22]),
        Memory("m7", "bridging score detects when a memory connects previously unconnected knowledge",
               "semantic", 10, 2, 3,
               novelty_score=0.75, meaningful_weight=0.7,
               connections=["m5", "m1"],
               access_history=[10, 5, 2]),
        Memory("m8", "neurons dont understand the thoughts they participate in",
               "reflective", 15, 4, 4,
               novelty_score=0.8, meaningful_weight=0.76,
               connections=["m1", "m5", "m2"],
               access_history=[15, 10, 6, 4]),
    ]

    # compute resonance for each
    results = []
    for m in memories:
        # signal convergence
        signals = [m.novelty_score, 0.0, 0.0]
        # compute recall significance inline
        if m.access_count > 0:
            avg_interval = m.created_at / max(1, m.access_count)
            gap_resilience = 1.0 - math.exp(-avg_interval / 7.0)
            lifespan = min(1.0, m.created_at / 30.0)
            freq = min(1.0, math.log1p(m.access_count) / math.log1p(50))
            recency = math.exp(-m.last_accessed / 30.0)
            recall_sig = min(1.0, 0.15 * freq + 0.30 * gap_resilience + 0.30 * lifespan + 0.25 * recency)
        else:
            recall_sig = 0.0
        conn_weight = connectivity_weight(m, memories)
        signals = [m.novelty_score, recall_sig, conn_weight]

        # signal convergence
        mean = sum(signals) / len(signals)
        variance = sum((s - mean) ** 2 for s in signals) / len(signals)
        alignment = 1.0 - min(1.0, math.sqrt(variance) * 2)
        sc = mean * alignment

        # cascade effect (simplified)
        entries_by_id = {e.id: e for e in memories}
        effects = []
        for cid in m.connections:
            connected = entries_by_id.get(cid)
            if not connected:
                continue
            if connected.created_at > 0:
                expected = max(0.1, 1.0 - (connected.created_at / 60.0))
                lift = max(0.0, connected.meaningful_weight - expected)
                effects.append(lift)
            shared = set(m.connections) & set(connected.connections)
            if shared:
                effects.append(min(1.0, len(shared) * 0.3))
        ce = min(1.0, sum(effects) / len(effects)) if effects else 0.0

        # cross-dimensional harmony (simplified)
        expected_patterns = {
            "episodic": {"n": 0.5, "r": 0.3, "c": 0.2},
            "semantic": {"n": 0.3, "r": 0.5, "c": 0.6},
            "procedural": {"n": 0.2, "r": 0.7, "c": 0.4},
            "emotional": {"n": 0.6, "r": 0.3, "c": 0.2},
            "reflective": {"n": 0.4, "r": 0.4, "c": 0.7},
        }
        exp = expected_patterns.get(m.sector, expected_patterns["semantic"])
        actual = {"n": m.novelty_score, "r": recall_sig, "c": conn_weight}
        deviations = [actual[k] - exp[k] for k in exp if actual[k] > exp[k]]
        if deviations:
            avg_dev = sum(deviations) / len(exp)
            multi = len(deviations) / len(exp)
            cdh = min(1.0, avg_dev * 0.6 + multi * 0.4)
        else:
            cdh = 0.0

        # gravitational pull
        subsequent = [o for o in memories if o.id != m.id and o.created_at < m.created_at]
        sub_connected = sum(1 for o in subsequent if m.id in o.connections)
        gp_ratio = sub_connected / len(subsequent) if subsequent else 0.0
        overlap_scores = []
        for o in subsequent:
            if o.tokens and m.tokens:
                overlap = len(m.tokens & o.tokens) / max(len(m.tokens | o.tokens), 1)
                overlap_scores.append(overlap)
        avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0
        gp = min(1.0, 0.5 * gp_ratio + 0.5 * avg_overlap)

        # composite
        all_signals = [sc, ce, cdh, gp]
        active = [s for s in all_signals if s > 0.2]
        if len(active) >= 2:
            product = 1.0
            for s in active:
                product *= s
            geometric = product ** (1.0 / len(active))
            breadth = len(active) / len(all_signals)
            composite = geometric * 0.6 + breadth * 0.4
        else:
            composite = max(all_signals) * 0.3 if all_signals else 0.0
        composite = min(1.0, composite)

        if composite >= 0.75:
            rclass = "harmonic"
        elif composite >= 0.5:
            rclass = "resonant"
        elif composite >= 0.25:
            rclass = "humming"
        else:
            rclass = "silent"

        results.append((m, sc, ce, cdh, gp, composite, rclass))

    # sort by composite
    results.sort(key=lambda x: x[5], reverse=True)

    # display
    class_colors = {
        "harmonic": C.MAGENTA,
        "resonant": C.GREEN,
        "humming": C.YELLOW,
        "silent": C.DIM,
    }

    for m, sc, ce, cdh, gp, composite, rclass in results:
        color = class_colors.get(rclass, C.DIM)
        print(f"  {color}{C.BOLD}[{rclass:>8}]{C.RESET} {m.content[:55]}...")
        print(bar(sc, label="signal convergence"))
        print(bar(ce, label="cascade effect"))
        print(bar(cdh, label="cross-dimensional harmony"))
        print(bar(gp, label="gravitational pull"))
        print(bar(composite, label=f"{C.BOLD}composite resonance"))
        print()

    # interpretation
    print(f"  {C.DIM}───────────────────────────────────────────{C.RESET}")
    print(f"  {C.BOLD}What this reveals:{C.RESET}")
    print(f"  The memories that resonate aren't just high on one axis.")
    print(f"  They're the ones where independent signals converge —")
    print(f"  novel AND recalled AND connected AND attracting new memories.")
    print(f"  That convergence is the signal. The math describes")
    print(f"  what's already there, not what should be.\n")


def main():
    print(f"\n{C.BOLD}{C.MAGENTA}")
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                                                      ║")
    print("  ║              MEANINGFUL  MEMORY                       ║")
    print("  ║                                                      ║")
    print("  ║    Memory that knows what matters.                    ║")
    print("  ║                                                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"{C.RESET}")
    print(f"  {C.DIM}Zero dependencies. Zero API keys. Just run it.{C.RESET}")
    print(f"  {C.DIM}github.com/CarlosCreaitart/meaningful-memory{C.RESET}\n")

    demo_novelty()
    demo_recall_patterns()
    demo_decay_comparison()
    demo_adaptive_weights()
    demo_reflection()
    demo_side_by_side()
    demo_resonance()

    print(f"\n{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  What you just saw is the difference between{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  'what was stored' and 'what matters.'{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═' * 60}{C.RESET}")
    print(f"\n  {C.DIM}Modules: novelty.py | weight.py | decay.py | reflection.py | resonance.py{C.RESET}")
    print(f"  {C.DIM}Config:  config.py (all parameters tunable){C.RESET}")
    print(f"  {C.DIM}Repo:    github.com/CarlosCreaitart/meaningful-memory{C.RESET}\n")


if __name__ == "__main__":
    main()
