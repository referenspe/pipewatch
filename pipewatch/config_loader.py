"""Utilities for discovering and merging pipewatch configuration."""
from __future__ import annotations

import os
from pathlib import Path

from pipewatch.config import PipewatchConfig

DEFAULT_CONFIG_NAMES = ("pipewatch.json", ".pipewatch.json")
_ENV_VAR = "PIPEWATCH_CONFIG"


def find_config_file(search_dir: str | Path | None = None) -> Path | None:
    """Search for a config file in *search_dir* (defaults to cwd)."""
    base = Path(search_dir) if search_dir else Path.cwd()
    for name in DEFAULT_CONFIG_NAMES:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None


def load_config(
    path: str | Path | None = None,
    search_dir: str | Path | None = None,
) -> PipewatchConfig:
    """Load config from *path*, env var, or auto-discovery.

    Resolution order:
    1. Explicit *path* argument
    2. ``PIPEWATCH_CONFIG`` environment variable
    3. Auto-discovery in *search_dir* / cwd
    4. Empty default config
    """
    resolved: Path | None = None

    if path is not None:
        resolved = Path(path)
    elif _ENV_VAR in os.environ:
        resolved = Path(os.environ[_ENV_VAR])
    else:
        resolved = find_config_file(search_dir)

    if resolved is not None:
        return PipewatchConfig.from_file(resolved)

    return PipewatchConfig()
