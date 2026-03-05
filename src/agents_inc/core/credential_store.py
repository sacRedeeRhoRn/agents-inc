from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from agents_inc.core.fabric_lib import dump_yaml, load_yaml
from agents_inc.core.util.time import now_iso


def _default_connections_dir() -> Path:
    return (Path.home() / ".agents-inc" / "connections").expanduser().resolve()


def _profile_path(profile_name: str, root: Optional[Path] = None) -> Path:
    base = (root or _default_connections_dir()).expanduser().resolve()
    return base / f"{profile_name}.yaml"


def load_connection_profile(profile_name: str, root: Optional[Path] = None) -> Dict[str, object]:
    path = _profile_path(profile_name, root)
    if not path.exists():
        return {}
    payload = load_yaml(path)
    if isinstance(payload, dict):
        return payload
    return {}


def save_connection_profile(
    *,
    profile_name: str,
    values: Dict[str, object],
    root: Optional[Path] = None,
) -> Path:
    path = _profile_path(profile_name, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "profile_name": profile_name,
        **values,
        "updated_at": now_iso(),
    }
    dump_yaml(path, payload)
    return path


def save_keychain_secret(service_name: str, key: str, secret: str) -> bool:
    if not service_name or not key:
        return False
    try:
        import keyring  # type: ignore

        keyring.set_password(service_name, key, secret)
        return True
    except Exception:
        return False
