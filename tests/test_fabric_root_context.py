#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents_inc.core.fabric_lib import default_fabric_root  # noqa: E402


class FabricRootContextTests(unittest.TestCase):
    def test_default_fabric_root_prefers_global_context_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "workspace"
            base.mkdir(parents=True, exist_ok=True)
            context_fabric = Path(td) / "ctx-fabric"
            for rel in ("catalog", "templates", "schemas"):
                (context_fabric / rel).mkdir(parents=True, exist_ok=True)

            with patch(
                "agents_inc.core.fabric_lib.load_global_context",
                return_value={"fabric_root": str(context_fabric)},
            ):
                resolved = default_fabric_root(cwd=base)
            self.assertEqual(resolved, context_fabric.resolve())

    def test_explicit_fabric_cwd_overrides_global_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "local-fabric"
            for rel in ("catalog", "templates", "schemas"):
                (base / rel).mkdir(parents=True, exist_ok=True)
            context_fabric = Path(td) / "ctx-fabric"
            for rel in ("catalog", "templates", "schemas"):
                (context_fabric / rel).mkdir(parents=True, exist_ok=True)

            with patch(
                "agents_inc.core.fabric_lib.load_global_context",
                return_value={"fabric_root": str(context_fabric)},
            ):
                resolved = default_fabric_root(cwd=base)
            self.assertEqual(resolved, base.resolve())


if __name__ == "__main__":
    unittest.main()
