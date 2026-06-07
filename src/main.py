"""Exocortex main entry — single asyncio loop, FastAPI + Textual coexist."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from .config import CortexConfig
from .bus import CorticalBus
from .compute import ComputeEngine
from .memory import MemoryLayer
from .protocols import create_app
from .tui import ExocortexTUI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("exocortex")


async def main(config: CortexConfig | None = None) -> None:
    """Run the exocortex: bus + compute + memory + server + TUI in one loop."""
    config = config or CortexConfig.load()

    logger.info(f"🧠 Exocortex starting: {config.name}")

    # Core components
    bus = CorticalBus()
    compute = ComputeEngine()
    memory = MemoryLayer()

    # Start the bus
    await bus.start()

    # FastAPI app
    app = create_app(bus, compute, memory)

    # Uvicorn in the same loop
    import uvicorn
    server = uvicorn.Config(app, host=config.host, port=config.port, log_level="warning")
    server_instance = uvicorn.Server(server)

    # TUI
    tui = ExocortexTUI(bus)

    # Periodic tasks
    async def memory_ticker():
        """Run memory cooling every 60s."""
        while True:
            await asyncio.sleep(60)
            stats = await memory.tick()
            if stats.get("pruned"):
                logger.info(f"Memory tick: {stats}")

    async def stats_updater():
        """Update TUI stats every 2s."""
        while True:
            await asyncio.sleep(2)
            tui.update_stats(
                agents=1,  # placeholder
                memories=memory.stats["total"],
                models=compute.stats.get("models", 0),
            )

    # Launch everything
    logger.info(f"📡 Server: http://{config.host}:{config.port}")
    logger.info(f"🔮 TUI: Plato's Cave")

    await asyncio.gather(
        server_instance.serve(),
        tui.run_async(),
        memory_ticker(),
        stats_updater(),
    )


def run() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exocortex shutting down")


if __name__ == "__main__":
    run()
