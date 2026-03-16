from __future__ import annotations

from typing import Any, Protocol


class PatientModel(Protocol):
    async def generate_response(self, state: Any, clinician_input: str) -> str:
        """Generate a simulated patient response for a given dialogue state and clinician input."""
        ...

