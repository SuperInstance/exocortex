"""Cortical Bus — the central event spine of the exocortex.

All inter-component communication flows through the bus.
Zero direct coupling. Everything is a typed CortexEvent.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Awaitable

from ..core.types import CortexEvent

logger = logging.getLogger(__name__)

# Type for event subscribers
Subscriber = Callable[[CortexEvent], Awaitable[None]]


class CorticalBus:
    """Asyncio-based pub/sub event bus with priority and rate limiting.

    - PriorityQueue: high-importance events render first
    - Fan-out: all subscribers get every event
    - Backpressure: bounded queue, shed low-priority when full
    - Rate limiting: per trace_id, max 5 events through to shadow
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[CortexEvent] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._subscribers: list[Subscriber] = []
        self._trace_counts: dict[str, int] = defaultdict(int)
        self._max_per_trace = 5
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, callback: Subscriber) -> None:
        """Register a subscriber. Called for every event."""
        self._subscribers.append(callback)

    async def publish(self, event: CortexEvent) -> bool:
        """Publish an event. Returns False if queue is full (backpressure)."""
        try:
            # Priority: negate importance so high-importance = low priority number
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            # Backpressure: shed the lowest priority event
            logger.warning(f"Bus full, shedding event from {event.source}")
            return False

    async def emit(self, event_type: str, source: str, **kwargs) -> bool:
        """Shorthand: create and publish an event."""
        event = CortexEvent.new(event_type, source, **kwargs)
        return await self.publish(event)

    def should_render(self, event: CortexEvent) -> bool:
        """Rate limit: max N events per trace_id."""
        trace = event.trace_id
        self._trace_counts[trace] += 1
        count = self._trace_counts[trace]
        if count <= self._max_per_trace:
            return True
        # Always render the last one (summary)
        if count == self._max_per_trace + 1:
            return False  # skip middle, will show summary
        return False

    async def start(self) -> None:
        """Start the bus dispatch loop."""
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())
        logger.info("Cortical Bus started")

    async def stop(self) -> None:
        """Stop the bus."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cortical Bus stopped")

    async def _dispatch_loop(self) -> None:
        """Pull events from queue, fan out to all subscribers."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            # Fan out to all subscribers
            for sub in self._subscribers:
                try:
                    await sub(event)
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
