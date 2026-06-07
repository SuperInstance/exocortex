"""Configuration loader — reads .cortex.toml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclass
class CortexConfig:
    """The single source of truth for exocortex configuration."""

    # Identity
    name: str = "default-cortex"

    # Memory
    memory_backend: str = "memory"  # "memory" | "surrealdb"
    memory_retention_days: float = 30.0
    embedding_dims: int = 384
    hot_window_seconds: float = 60.0
    warm_unreinforced_hours: float = 24.0
    cold_confidence_threshold: float = 0.1
    lru_max: int = 500

    # Compute
    default_model: str = "micronn"
    max_training_ms: float = 5000.0

    # Server
    host: str = "0.0.0.0"
    port: int = 9000

    # Protocols
    a2a_enabled: bool = True
    mcp_enabled: bool = True
    rest_cors_origins: list[str] = field(default_factory=lambda: ["*"])

    # TUI
    default_shadow_mode: str = "stream"
    dream_idle_seconds: float = 30.0

    @classmethod
    def load(cls, path: Path | str = ".cortex.toml") -> CortexConfig:
        """Load from TOML file, falling back to defaults."""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        cortex = data.get("cortex", {})
        mem = data.get("memory", {})
        comp = data.get("compute", {})
        srv = data.get("server", {})
        proto = data.get("protocols", {})
        tui = data.get("tui", {})

        return cls(
            name=cortex.get("name", "default-cortex"),
            memory_backend=mem.get("backend", "memory"),
            memory_retention_days=mem.get("retention", "30d").rstrip("d"),
            embedding_dims=mem.get("embedding_dims", 384),
            hot_window_seconds=mem.get("hot_window_seconds", 60.0),
            warm_unreinforced_hours=mem.get("warm_unreinforced_hours", 24.0),
            cold_confidence_threshold=mem.get("cold_confidence_threshold", 0.1),
            lru_max=mem.get("lru_max", 500),
            default_model=comp.get("default_model", "micronn"),
            max_training_ms=comp.get("max_training_ms", 5000.0),
            host=srv.get("host", "0.0.0.0"),
            port=srv.get("port", 9000),
            a2a_enabled=proto.get("a2a_enabled", True),
            mcp_enabled=proto.get("mcp_enabled", True),
            rest_cors_origins=proto.get("rest_cors_origins", ["*"]),
            default_shadow_mode=tui.get("default_shadow_mode", "stream"),
            dream_idle_seconds=tui.get("dream_idle_seconds", 30.0),
        )
