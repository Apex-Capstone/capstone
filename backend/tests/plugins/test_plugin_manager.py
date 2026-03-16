from __future__ import annotations

from types import SimpleNamespace
import sys

import pytest

from core import plugin_manager


class _DummyPatientModel:
    def __init__(self) -> None:
        self.created = True

    async def generate_response(self, state, clinician_input: str) -> str:  # pragma: no cover - behavior not under test
        return "dummy"


class _DummyEvaluator:
    async def evaluate(self, db, session_id: int):  # pragma: no cover - behavior not under test
        return None


class _DummyMetricsPlugin:
    def __init__(self) -> None:
        self.created = True

    def compute(self, db, session_id: int) -> dict:
        return {}


def _make_settings(**kwargs):
    defaults = {
        "patient_model_plugin": "",
        "evaluator_plugin": "",
        "metrics_plugins": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def teardown_function() -> None:
    # Ensure per-test isolation for lru_cache-backed accessors
    plugin_manager.get_patient_model.cache_clear()
    plugin_manager.get_evaluator.cache_clear()
    plugin_manager.get_metrics_plugins.cache_clear()


def test_loads_class_from_module_path():
    path = f"{__name__}:_DummyPatientModel"

    cls = plugin_manager._load_class_from_path(path)

    assert cls is _DummyPatientModel


def test_invalid_plugin_path_raises_value_error():
    with pytest.raises(ValueError):
        plugin_manager._load_class_from_path("not-a-valid-path")


def test_invalid_plugin_module_raises_import_error():
    with pytest.raises(ImportError):
        plugin_manager._load_class_from_path("non.existent.module:SomeClass")


def test_invalid_plugin_class_raises_import_error():
    # Module exists but class does not
    path = f"{__name__}:NonExistentClass"
    with pytest.raises(ImportError):
        plugin_manager._load_class_from_path(path)


def test_get_patient_model_uses_cached_instance(monkeypatch: pytest.MonkeyPatch):
    created = {"count": 0}

    class CountingPatientModel(_DummyPatientModel):
        def __init__(self) -> None:
            created["count"] += 1
            super().__init__()

    # Expose the class as a real module attribute so importlib can find it
    setattr(sys.modules[__name__], "CountingPatientModel", CountingPatientModel)

    path = f"{__name__}:CountingPatientModel"

    monkeypatch.setattr(
        plugin_manager, "get_settings", lambda: _make_settings(patient_model_plugin=path)
    )

    first = plugin_manager.get_patient_model()
    second = plugin_manager.get_patient_model()

    assert first is second
    assert created["count"] == 1


def test_get_evaluator_uses_cached_instance(monkeypatch: pytest.MonkeyPatch):
    created = {"count": 0}

    class CountingEvaluator(_DummyEvaluator):
        def __init__(self) -> None:
            created["count"] += 1

    setattr(sys.modules[__name__], "CountingEvaluator", CountingEvaluator)

    path = f"{__name__}:CountingEvaluator"

    monkeypatch.setattr(
        plugin_manager, "get_settings", lambda: _make_settings(evaluator_plugin=path)
    )

    first = plugin_manager.get_evaluator()
    second = plugin_manager.get_evaluator()

    assert first is second
    assert created["count"] == 1


def test_get_metrics_plugins_returns_cached_instances(monkeypatch: pytest.MonkeyPatch):
    created = {"count": 0}

    class CountingMetricsPlugin(_DummyMetricsPlugin):
        def __init__(self) -> None:
            created["count"] += 1
            super().__init__()

    setattr(sys.modules[__name__], "CountingMetricsPlugin", CountingMetricsPlugin)

    path = f"{__name__}:CountingMetricsPlugin"

    monkeypatch.setattr(
        plugin_manager,
        "get_settings",
        lambda: _make_settings(metrics_plugins=[path, path]),
    )

    first = plugin_manager.get_metrics_plugins()
    second = plugin_manager.get_metrics_plugins()

    # Same tuple object due to caching
    assert first is second
    # Underlying constructor called twice (two plugins in config) but not on second call
    assert created["count"] == 2

