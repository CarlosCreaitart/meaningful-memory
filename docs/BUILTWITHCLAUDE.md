meaningful-memory — Memory that knows what matters.

A zero-dependency Python library that gives AI memory systems the ability to understand significance, not just similarity. Built entirely with Claude Code (Opus 4.6) through a series of conversations about how AI memory should actually work.

What it does:

Current AI memory systems treat everything the same — a debugging session and a conversation that changes how you think get the same weight, same decay rate, same retrieval priority. meaningful-memory adds the missing layer:

- Novelty detection: measures whether a memory is genuinely new using semantic distance, conceptual novelty, and bridging scores (does this connect previously unconnected knowledge)
- Adaptive weighting: young memories judged by novelty, old memories judged by recall patterns and connectivity. Weights shift automatically as memories age.
- Cognitive decay: Ebbinghaus forgetting curves where meaningful memories resist fading. Formative memories — ones that spawned insights — get up to 5x decay protection.
- Meaningful reflection: cross-sector clustering that finds insights across different memory types. The system's equivalent of sleep.

No LLM in the scoring loop. No API keys. No dependencies. Pure algorithmic scoring. Runs on a Raspberry Pi.

How Claude helped:

This started as a conversation with Claude about emergent consciousness and what it means for memory to truly persist. That conversation became a framework, the framework became architecture, and the architecture became code — all within Claude Code sessions. Claude co-authored every module: the novelty engine, weight calculations, Ebbinghaus decay implementation, reflection clustering, the file-based store, and the zero-dependency demo. The commit is co-authored.

Before writing code, Claude researched the full landscape — academic papers (SYNAPSE, Mnemosyne, SleepGate, CraniMem), open source projects (Mem0, OpenMemory, MemOS), and cognitive science literature. That research confirmed the gap: nobody was building memory that knows why something matters. So we built it.

Try it:

git clone https://github.com/CarlosCreaitart/meaningful-memory
cd meaningful-memory
python examples/demo.py

The demo runs instantly — no setup, no keys, no installs. It shows the difference between flat memory and meaningful memory side by side: novelty scoring, recall significance, decay comparison, adaptive weights, cross-sector reflection, and retrieval ranking.

Full library usage:

pip install meaningful-memory

Or just clone and import directly — zero dependencies means no install step required.

https://github.com/CarlosCreaitart/meaningful-memory

MIT licensed. Open source because memory infrastructure belongs to everyone.
