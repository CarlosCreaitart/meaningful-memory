"""
Lightweight file-based memory store.

Zero dependencies. Human-readable YAML+Markdown files.
Runs on anything — Raspberry Pi to Mac Studio.

This is the default store. For integration with OpenMemory,
Mem0, or other systems, use the adapter pattern:
your system stores memories, meaningful-memory scores them.
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class MemoryEntry:
    """A single memory with its significance metadata."""
    id: str = ""
    content: str = ""
    sector: str = "semantic"  # episodic, semantic, procedural, emotional, reflective
    created_at: float = 0.0  # unix timestamp
    last_accessed: float = 0.0
    access_count: int = 0
    access_history: List[float] = field(default_factory=list)
    salience: float = 0.5
    tags: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # weight signals
    novelty_score: float = 0.0
    recall_significance: float = 0.0
    connectivity_weight: float = 0.0
    meaningful_weight: float = 0.0

    # state
    is_formative: bool = False
    decay_state: str = "active"  # active, fading, trace
    consolidated: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_accessed:
            self.last_accessed = self.created_at

    @property
    def age_days(self) -> float:
        return max(0, (time.time() - self.created_at) / 86400)

    @property
    def gap_days(self) -> float:
        return max(0, (time.time() - self.last_accessed) / 86400)

    @property
    def tokens(self) -> set:
        """Simple tokenization for similarity calculations."""
        stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "can", "shall",
                "to", "of", "in", "for", "on", "with", "at", "by", "from",
                "it", "this", "that", "and", "or", "but", "not", "as", "if"}
        words = set(self.content.lower().split())
        return words - stop

    def record_access(self):
        """Record that this memory was accessed/recalled."""
        now = time.time()
        self.access_count += 1
        self.last_accessed = now
        self.access_history.append(now)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_file_content(self) -> str:
        """Serialize to human-readable YAML+Markdown format."""
        lines = ["---"]
        lines.append(f"id: {self.id}")
        lines.append(f"sector: {self.sector}")
        lines.append(f"created_at: {self.created_at}")
        lines.append(f"last_accessed: {self.last_accessed}")
        lines.append(f"access_count: {self.access_count}")
        lines.append(f"salience: {self.salience:.4f}")
        lines.append(f"meaningful_weight: {self.meaningful_weight:.4f}")
        lines.append(f"novelty_score: {self.novelty_score:.4f}")
        lines.append(f"recall_significance: {self.recall_significance:.4f}")
        lines.append(f"connectivity_weight: {self.connectivity_weight:.4f}")
        lines.append(f"is_formative: {self.is_formative}")
        lines.append(f"decay_state: {self.decay_state}")
        lines.append(f"consolidated: {self.consolidated}")
        if self.tags:
            lines.append(f"tags: {json.dumps(self.tags)}")
        if self.connections:
            lines.append(f"connections: {json.dumps(self.connections)}")
        lines.append("---")
        lines.append("")
        lines.append(self.content)
        return "\n".join(lines)

    @classmethod
    def from_file_content(cls, text: str) -> "MemoryEntry":
        """Deserialize from YAML+Markdown format."""
        if not text.startswith("---"):
            return cls(content=text)

        parts = text.split("---", 2)
        if len(parts) < 3:
            return cls(content=text)

        frontmatter = parts[1].strip()
        content = parts[2].strip()

        data = {"content": content}
        for line in frontmatter.split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key in ("tags", "connections", "access_history"):
                try:
                    data[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    data[key] = []
            elif key in ("created_at", "last_accessed", "salience",
                         "meaningful_weight", "novelty_score",
                         "recall_significance", "connectivity_weight"):
                try:
                    data[key] = float(value)
                except ValueError:
                    pass
            elif key == "access_count":
                try:
                    data[key] = int(value)
                except ValueError:
                    pass
            elif key in ("is_formative", "consolidated"):
                data[key] = value.lower() == "true"
            else:
                data[key] = value

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MemoryStore:
    """
    File-based memory store.

    Directory structure:
        memories/
        ├── active/         # living memories
        ├── fading/         # low-salience, archived
        ├── reflections/    # generated insights
        └── index.json      # lightweight index
    """

    def __init__(self, path: str = "./memories"):
        self.path = Path(path)
        self._ensure_dirs()
        self._index: Dict[str, dict] = {}
        self._load_index()

    def _ensure_dirs(self):
        for subdir in ["active", "fading", "reflections"]:
            (self.path / subdir).mkdir(parents=True, exist_ok=True)

    def _index_path(self) -> Path:
        return self.path / "index.json"

    def _load_index(self):
        idx_path = self._index_path()
        if idx_path.exists():
            try:
                self._index = json.loads(idx_path.read_text())
            except (json.JSONDecodeError, ValueError):
                self._index = {}
                self._rebuild_index()
        else:
            self._rebuild_index()

    def _save_index(self):
        self._index_path().write_text(json.dumps(self._index, indent=2))

    def _rebuild_index(self):
        """Rebuild index from files on disk."""
        self._index = {}
        for subdir in ["active", "fading", "reflections"]:
            dir_path = self.path / subdir
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                try:
                    entry = MemoryEntry.from_file_content(f.read_text())
                    self._index[entry.id] = {
                        "sector": entry.sector,
                        "weight": entry.meaningful_weight,
                        "salience": entry.salience,
                        "state": subdir,
                        "file": str(f.relative_to(self.path)),
                    }
                except Exception:
                    continue
        self._save_index()

    def add(self, content: str, sector: str = "semantic",
            tags: Optional[List[str]] = None,
            metadata: Optional[Dict] = None) -> MemoryEntry:
        """Store a new memory."""
        entry = MemoryEntry(
            content=content,
            sector=sector,
            tags=tags or [],
            metadata=metadata or {},
        )

        filepath = self.path / "active" / f"{entry.id}.md"
        filepath.write_text(entry.to_file_content())

        self._index[entry.id] = {
            "sector": sector,
            "weight": 0.0,
            "salience": entry.salience,
            "state": "active",
            "file": f"active/{entry.id}.md",
        }
        self._save_index()

        return entry

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        info = self._index.get(memory_id)
        if not info:
            return None

        filepath = self.path / info["file"]
        if not filepath.exists():
            return None

        return MemoryEntry.from_file_content(filepath.read_text())

    def get_all(self, state: str = "active", limit: int = 100) -> List[MemoryEntry]:
        """Get all memories in a given state."""
        entries = []
        dir_path = self.path / state
        if not dir_path.exists():
            return entries

        files = sorted(dir_path.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[:limit]:
            try:
                entries.append(MemoryEntry.from_file_content(f.read_text()))
            except Exception:
                continue

        return entries

    def update(self, entry: MemoryEntry):
        """Update a memory on disk."""
        info = self._index.get(entry.id)
        if not info:
            return

        filepath = self.path / info["file"]
        filepath.write_text(entry.to_file_content())

        self._index[entry.id]["weight"] = entry.meaningful_weight
        self._index[entry.id]["salience"] = entry.salience
        self._save_index()

    def move_to_fading(self, memory_id: str):
        """Move a memory from active to fading."""
        info = self._index.get(memory_id)
        if not info or info["state"] != "active":
            return

        old_path = self.path / info["file"]
        new_path = self.path / "fading" / f"{memory_id}.md"

        if old_path.exists():
            new_path.write_text(old_path.read_text())
            old_path.unlink()

        self._index[memory_id]["state"] = "fading"
        self._index[memory_id]["file"] = f"fading/{memory_id}.md"
        self._save_index()

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Simple token-overlap search.

        For production use, integrate with an embedding provider.
        This is the fallback that works without any dependencies.
        """
        query_tokens = set(query.lower().split())
        scored = []

        for entry in self.get_all("active", limit=200):
            overlap = len(query_tokens & entry.tokens)
            if overlap > 0:
                score = overlap / max(len(query_tokens), 1)
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, _ in scored[:limit]]

    def connect(self, id_a: str, id_b: str):
        """Create a bidirectional connection between two memories."""
        a = self.get(id_a)
        b = self.get(id_b)

        if a and b:
            if id_b not in a.connections:
                a.connections.append(id_b)
                self.update(a)
            if id_a not in b.connections:
                b.connections.append(id_a)
                self.update(b)

    @property
    def count(self) -> int:
        return len(self._index)

    def stats(self) -> Dict[str, Any]:
        """Summary statistics for the memory store."""
        active = [v for v in self._index.values() if v["state"] == "active"]
        fading = [v for v in self._index.values() if v["state"] == "fading"]

        sectors = {}
        for v in self._index.values():
            s = v.get("sector", "unknown")
            sectors[s] = sectors.get(s, 0) + 1

        return {
            "total": len(self._index),
            "active": len(active),
            "fading": len(fading),
            "sectors": sectors,
            "avg_weight": sum(v.get("weight", 0) for v in active) / max(1, len(active)),
        }
