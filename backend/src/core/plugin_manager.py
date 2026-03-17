from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, Iterable, Type

from config.settings import get_settings
from interfaces.evaluator import Evaluator
from interfaces.metrics import MetricsPlugin
from interfaces.patient_model import PatientModel


def _load_class_from_path(path: str) -> Type[Any]:
    """
    Load a class from a string path of the form "module.path:ClassName".

    Raises a ValueError for malformed paths, and ImportError with a clear
    message if the module or class cannot be imported.
    """
    if ":" not in path:
        raise ValueError(
            f"Invalid plugin path '{path}'. Expected format 'module.path:ClassName'."
        )

    module_path, class_name = path.split(":", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Could not import plugin module '{module_path}' for path '{path}'."
        ) from exc

    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ImportError(
            f"Module '{module_path}' does not define plugin class '{class_name}'."
        ) from exc

    return cls


def _instantiate_plugins(paths: Iterable[str]) -> list[Any]:
    instances: list[Any] = []
    for path in paths:
        if not path:
            continue
        cls = _load_class_from_path(path)
        instances.append(cls())
    return instances


@lru_cache()
def get_patient_model() -> PatientModel:
    """
    Return the configured PatientModel plugin instance.

    The plugin path is expected to be provided via settings as
    `settings.patient_model_plugin` in the format "module.path:ClassName".
    """
    settings = get_settings()
    plugin_path: str | None = getattr(settings, "patient_model_plugin", None)

    if not plugin_path:
        raise RuntimeError(
            "Patient model plugin path is not configured "
            "(missing 'patient_model_plugin' in settings)."
        )

    cls = _load_class_from_path(plugin_path)
    return cls()  # type: ignore[return-value]


@lru_cache()
def get_evaluator() -> Evaluator:
    """
    Return the configured Evaluator plugin instance.

    The plugin path is expected to be provided via settings as
    `settings.evaluator_plugin` in the format "module.path:ClassName".
    """
    settings = get_settings()
    plugin_path: str | None = getattr(settings, "evaluator_plugin", None)

    if not plugin_path:
        raise RuntimeError(
            "Evaluator plugin path is not configured "
            "(missing 'evaluator_plugin' in settings)."
        )

    cls = _load_class_from_path(plugin_path)
    return cls()  # type: ignore[return-value]


@lru_cache()
def get_metrics_plugins() -> tuple[MetricsPlugin, ...]:
    """
    Return the configured MetricsPlugin instances as a cached tuple.

    The plugin paths are expected to be provided via settings as
    `settings.metrics_plugins`, an iterable of strings in the format
    "module.path:ClassName".
    """
    settings = get_settings()
    paths: Iterable[str] = getattr(settings, "metrics_plugins", []) or []

    instances = _instantiate_plugins(paths)
    return tuple(instances)  # type: ignore[return-value]

