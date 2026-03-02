"""Framework-level error types.

Kept in a leaf module (no internal imports) so every other util module can
import FabricError without creating circular dependencies.
"""
from __future__ import annotations


class FabricError(RuntimeError):
    """Raised for any unrecoverable agents-inc framework error."""
