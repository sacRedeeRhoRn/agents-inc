"""Framework-level version and naming constants.

Kept in a leaf module (no internal imports) so every util module can import
these without creating circular dependencies.
"""
from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION: str = "3.0"
TEMPLATE_VERSION: str = "3.0.0"
BUNDLE_VERSION: str = "3.0.0"
ROUTER_SKILL_NAME: str = "research-router"
DEFAULT_INSTALL_TARGET: str = str(Path.home() / ".codex" / "skills" / "local")
