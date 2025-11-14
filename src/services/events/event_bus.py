"""Thread-safe event bus using Observer pattern with queue-based dispatch."""

import queue
import threading
from typing import Any, Callable, Dict, List, Optional

from src.utils.logger import get_logger
from src.core.enums.events import DownloadEvent

logger = get_logger(__name__)




class DownloadEventBus:
    """Thread-safe event bus using queue-based dispatch."""

    def __init__(self, root: Optional[Any] = None):
        self._listeners: Dict[DownloadEvent, List[Callable]] = {
            event: [] for event in DownloadEvent
        }
        self._event_queue: queue.Queue = queue.Queue()
        self._root = root
        self._processing = False
        self._lock = threading.Lock()

        logger.info(f"[EVENT_BUS] Initialized with root: {root is not None}")

        # Start processing immediately if root is provided
        if self._root:
            logger.info("[EVENT_BUS] Root provided, starting event processing")
            self._start_processing()
        else:
            logger.warning(
                "[EVENT_BUS] No root provided - event processing NOT started"
            )

    def set_root(self, root: Any) -> None:
        """Set the root window and start processing."""
        logger.info(f"[EVENT_BUS] set_root called, processing: {self._processing}")
        self._root = root
        self._start_processing()

    def subscribe(self, event: DownloadEvent, callback: Callable) -> None:
        """Subscribe to an event."""
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)
            logger.debug(
                f"[EVENT_BUS] Subscribed to {event.name}, total listeners: {len(self._listeners[event])}"
            )

    def unsubscribe(self, event: DownloadEvent, callback: Callable) -> None:
        """Unsubscribe from an event."""
        with self._lock:
            if event in self._listeners and callback in self._listeners[event]:
                self._listeners[event].remove(callback)
                logger.debug(f"[EVENT_BUS] Unsubscribed from {event.name}")

    def publish(self, event: DownloadEvent, **kwargs) -> None:
        """Publish an event - adds to queue for processing on main thread."""
        self._event_queue.put((event, kwargs))
        logger.debug(
            f"[EVENT_BUS] Event {event.name} queued, queue size: {self._event_queue.qsize()}"
        )

    def _start_processing(self) -> None:
        """Start processing events on main thread."""
        if not self._root:
            logger.warning("[EVENT_BUS] Cannot start processing - no root window")
            return

        if self._processing:
            logger.debug("[EVENT_BUS] Processing already started, skipping")
            return

        logger.info("[EVENT_BUS] Starting event processing loop")
        self._processing = True
        self._process_events()

    def _process_events(self) -> None:
        """Process all queued events on main thread."""
        if not self._root:
            logger.error("[EVENT_BUS] _process_events called without root!")
            return

        try:
            # Process all queued events
            events_processed = 0
            queue_size = self._event_queue.qsize()

            while not self._event_queue.empty():
                try:
                    event, kwargs = self._event_queue.get_nowait()
                    self._dispatch_event(event, kwargs)
                    events_processed += 1
                except queue.Empty:
                    break

            if events_processed > 0:
                logger.info(
                    f"[EVENT_BUS] Processed {events_processed} events (queue was {queue_size})"
                )
            elif queue_size > 0:
                logger.warning(
                    f"[EVENT_BUS] Queue had {queue_size} items but processed 0"
                )

        except Exception as e:
            logger.error(f"[EVENT_BUS] Error processing events: {e}", exc_info=True)
        finally:
            # Schedule next processing cycle
            if self._processing:
                self._root.after(50, self._process_events)
            else:
                logger.warning(
                    "[EVENT_BUS] Processing stopped, not scheduling next cycle"
                )

    def _dispatch_event(self, event: DownloadEvent, kwargs: Dict[str, Any]) -> None:
        """Dispatch event to all subscribers."""
        with self._lock:
            listeners = self._listeners.get(event, []).copy()

        if not listeners:
            logger.warning(f"[EVENT_BUS] No listeners registered for {event.name}!")
            return

        logger.info(
            f"[EVENT_BUS] Dispatching {event.name} to {len(listeners)} listeners"
        )

        for i, callback in enumerate(listeners):
            try:
                logger.debug(
                    f"[EVENT_BUS] Calling listener {i + 1}/{len(listeners)} for {event.name}"
                )
                callback(**kwargs)
                logger.debug(f"[EVENT_BUS] Listener {i + 1} completed successfully")
            except Exception as e:
                logger.error(
                    f"[EVENT_BUS] Error in {event.name} callback {i + 1}: {e}",
                    exc_info=True,
                )

    def stop_processing(self) -> None:
        """Stop processing events."""
        logger.info("[EVENT_BUS] Stopping event processing")
        self._processing = False

    def clear(self) -> None:
        """Clear all subscriptions and queued events."""
        with self._lock:
            for event in DownloadEvent:
                self._listeners[event].clear()

        # Clear queue
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("[EVENT_BUS] Cleared all listeners and queued events")
