from __future__ import annotations

from typing import Any, Dict, Type


class PluginRegistry:
    """
    Lightweight, in-memory registry for pluggable components.

    The registry is intentionally simple and deterministic:
    - keys are plain strings
    - values are plugin classes (not instances)
    - lookups raise ValueError when a key is unknown
    """

    evaluators: Dict[str, Type[Any]] = {}
    patient_models: Dict[str, Type[Any]] = {}
    metrics_plugins: Dict[str, Type[Any]] = {}

    # --- Evaluators ---
    @classmethod
    def register_evaluator(cls, name: str, plugin_class: Type[Any]) -> None:
        cls.evaluators[name] = plugin_class

    @classmethod
    def get_evaluator(cls, name: str) -> Type[Any]:
        try:
            return cls.evaluators[name]
        except KeyError as exc:
            raise ValueError(f"Evaluator plugin not found: {name}") from exc

    @classmethod
    def list_evaluators(cls) -> Dict[str, Type[Any]]:
        return dict(cls.evaluators)

    # --- Patient models ---
    @classmethod
    def register_patient_model(cls, name: str, plugin_class: Type[Any]) -> None:
        cls.patient_models[name] = plugin_class

    @classmethod
    def get_patient_model(cls, name: str) -> Type[Any]:
        try:
            return cls.patient_models[name]
        except KeyError as exc:
            raise ValueError(f"Patient model plugin not found: {name}") from exc

    @classmethod
    def list_patient_models(cls) -> Dict[str, Type[Any]]:
        return dict(cls.patient_models)

    # --- Metrics plugins ---
    @classmethod
    def register_metrics_plugin(cls, name: str, plugin_class: Type[Any]) -> None:
        cls.metrics_plugins[name] = plugin_class

    @classmethod
    def get_metrics_plugin(cls, name: str) -> Type[Any]:
        try:
            return cls.metrics_plugins[name]
        except KeyError as exc:
            raise ValueError(f"Metrics plugin not found: {name}") from exc

    @classmethod
    def list_metrics_plugins(cls) -> Dict[str, Type[Any]]:
        return dict(cls.metrics_plugins)

