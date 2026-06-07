"""Textual TUI — Plato's Cave. Machine cognition rendered as human shadows."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, RichLog
from textual.reactive import reactive
from rich.text import Text

from ..core.types import CortexEvent, ShadowMode
from ..shadows import render_shadow, RenderedShadow, ShadowColor
from ..bus import CorticalBus

if TYPE_CHECKING:
    pass


RICH_COLORS = {
    ShadowColor.GREEN: "green",
    ShadowColor.YELLOW: "yellow",
    ShadowColor.RED: "bold red",
    ShadowColor.BLUE: "cyan",
    ShadowColor.MAGENTA: "magenta",
    ShadowColor.PURPLE: "dim purple",
}


class ShadowWall(RichLog):
    """The main firehose — shadows scroll up the wall."""

    DEFAULT_CSS = """
    ShadowWall {
        height: 1fr;
        border: round $primary;
        padding: 0 1;
    }
    """

    def add_shadow(self, shadow: RenderedShadow) -> None:
        """Write a shadow to the wall."""
        ts = datetime.fromtimestamp(shadow.timestamp).strftime("%H:%M:%S")
        color = RICH_COLORS.get(shadow.color, "white")
        text = Text()
        text.append(f"{ts} ", style="dim")
        text.append(shadow.glyph, style=color)
        self.write(text)


class StatsBar(Static):
    """Bottom stats bar."""

    DEFAULT_CSS = """
    StatsBar {
        height: 1;
        dock: bottom;
        background: $primary-background;
        color: $text;
        padding: 0 1;
    }
    """

    agents: reactive[int] = reactive(0)
    memories: reactive[int] = reactive(0)
    models: reactive[int] = reactive(0)

    def render(self) -> str:
        return (
            f"  │ 🤖 {self.agents} agents  "
            f"│ 💾 {self.memories} memories  "
            f"│ 🏋️ {self.models} models  "
            f"│ Mode: Stream │"
        )


class ExocortexTUI(App):
    """Plato's Cave — the exocortex visual interface."""

    TITLE = "Exocortex"
    CSS = """
    Screen {
        layout: vertical;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "toggle_mode", "Mode"),
        ("c", "clear", "Clear"),
    ]

    mode: reactive[str] = reactive("stream")

    def __init__(self, bus: CorticalBus, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bus = bus
        self._shadow_count = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield ShadowWall(id="wall")
        yield StatsBar(id="stats")
        yield Footer()

    async def on_mount(self) -> None:
        """Subscribe to the Cortical Bus."""
        self._bus.subscribe(self._on_event)

    async def _on_event(self, event: CortexEvent) -> None:
        """Handle a CortexEvent from the bus."""
        shadow = render_shadow(event)
        try:
            wall = self.query_one("#wall", ShadowWall)
            wall.add_shadow(shadow)
            self._shadow_count += 1
        except Exception:
            pass  # TUI not ready yet

    def update_stats(self, agents: int = 0, memories: int = 0, models: int = 0) -> None:
        """Update the stats bar."""
        try:
            stats = self.query_one("#stats", StatsBar)
            stats.agents = agents
            stats.memories = memories
            stats.models = models
        except Exception:
            pass

    def action_toggle_mode(self) -> None:
        modes = ["stream", "focus", "landscape"]
        idx = (modes.index(self.mode) + 1) % len(modes)
        self.mode = modes[idx]

    def action_clear(self) -> None:
        try:
            wall = self.query_one("#wall", ShadowWall)
            wall.clear()
        except Exception:
            pass
