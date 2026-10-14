"""Synchronous in-process event bus. Subscribers must remain non-blocking."""
from collections import deque
from datetime import datetime, timezone
from typing import Callable
import logging


class EventBus:
    def __init__(self):
        self.listeners: list[Callable] = []
        self.history = deque(maxlen=60)
        self.sequence = 0

    def subscribe(self, listener: Callable):
        self.listeners.append(listener)

    def emit(self, kind: str, **payload):
        self.sequence += 1
        event = {"id": self.sequence, "type": kind,
                 "at": datetime.now(timezone.utc).isoformat(), "payload": payload}
        self.history.appendleft(event)
        for listener in self.listeners:
            try:
                listener(event)
            except Exception:
                logging.exception("Event subscriber failed: %s", kind)
        return event
