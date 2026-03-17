from __future__ import annotations

import pytest

from plugins.registry import PluginRegistry


class _DummyEvaluator:
    pass


def teardown_function() -> None:
    # Ensure isolation between tests by clearing registry state.
    PluginRegistry.evaluators.clear()
    PluginRegistry.patient_models.clear()
    PluginRegistry.metrics_plugins.clear()


def test_register_and_get_evaluator():
    PluginRegistry.register_evaluator("test_evaluator", _DummyEvaluator)

    retrieved = PluginRegistry.get_evaluator("test_evaluator")

    assert retrieved is _DummyEvaluator


def test_get_unknown_evaluator_raises_value_error():
    with pytest.raises(ValueError):
        PluginRegistry.get_evaluator("does_not_exist")


def test_list_evaluators_returns_copy():
    PluginRegistry.register_evaluator("test_evaluator", _DummyEvaluator)

    listed = PluginRegistry.list_evaluators()

    assert "test_evaluator" in listed
    assert listed["test_evaluator"] is _DummyEvaluator
    # Mutating the returned dict must not affect internal state
    listed.clear()
    assert "test_evaluator" in PluginRegistry.evaluators

