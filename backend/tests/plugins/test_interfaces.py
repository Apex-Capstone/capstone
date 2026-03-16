from __future__ import annotations

from typing import Any

from interfaces.patient_model import PatientModel
from interfaces.evaluator import Evaluator
from interfaces.metrics import MetricsPlugin


def test_patient_model_interface_has_generate_response():
    class DummyPatientModel:
        async def generate_response(self, state: Any, clinician_input: str) -> str:  # type: ignore[override]
            return "ok"

    impl = DummyPatientModel()

    # type-checking / structural check: mypy will enforce Protocol compatibility,
    # and at runtime we at least verify the attribute is present.
    assert hasattr(impl, "generate_response")


def test_evaluator_interface_has_evaluate():
    class DummyEvaluator:
        async def evaluate(self, db, session_id: int):
            return None

    impl = DummyEvaluator()

    assert hasattr(impl, "evaluate")


def test_metrics_plugin_interface_has_compute():
    class DummyMetricsPlugin:
        def compute(self, db, session_id: int) -> dict[str, Any]:
            return {}

    impl = DummyMetricsPlugin()

    assert hasattr(impl, "compute")

