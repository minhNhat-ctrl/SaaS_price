"""YAML configuration loader for application layer.

API endpoints and flows should use this instead of importing yaml directly.
"""
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(config_name: str) -> Dict[str, Any]:
    """Load a YAML config file from application/config/.

    Args:
        config_name: File name, e.g. "identity.yaml".
    """
    config_path = Path(__file__).resolve().parents[1] / "config" / config_name
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_identity_config() -> Dict[str, Any]:
    """Convenience loader for identity.yaml."""
    return load_config("identity.yaml")
