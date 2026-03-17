from __future__ import annotations

from typing import Any, Protocol


class MetricsPlugin(Protocol):
    def compute(self, db, session_id: int) -> dict[str, Any]:
        """Compute additional, research-oriented metrics for a completed session."""
        ...

