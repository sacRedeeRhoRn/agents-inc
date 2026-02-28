#!/usr/bin/env bash
set -euo pipefail

OWNER="sacRedeeRhoRn"
REPO="agents-inc"
RELEASE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      OWNER="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --release)
      RELEASE="$2"
      shift 2
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$RELEASE" ]]; then
  echo "--release is required" >&2
  exit 1
fi

VERSION="${RELEASE#v}"
WHEEL="agents_inc-${VERSION}-py3-none-any.whl"
CHECKSUM_FILE="agents_inc-${VERSION}.sha256"
BASE_URL="https://github.com/${OWNER}/${REPO}/releases/download/${RELEASE}"

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

curl -sfL "${BASE_URL}/${WHEEL}" -o "${TMP_DIR}/${WHEEL}"
curl -sfL "${BASE_URL}/${CHECKSUM_FILE}" -o "${TMP_DIR}/${CHECKSUM_FILE}"

(
  cd "$TMP_DIR"
  WHEEL_LINE="$(grep "  ${WHEEL}$" "${CHECKSUM_FILE}" || true)"
  if [[ -z "${WHEEL_LINE}" ]]; then
    echo "checksum file does not contain ${WHEEL}" >&2
    exit 1
  fi
  printf "%s\n" "${WHEEL_LINE}" > wheel-only.sha256
  shasum -a 256 -c wheel-only.sha256
)

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install --upgrade "${TMP_DIR}/${WHEEL}"

python3 - <<'PY'
from pathlib import Path
import agents_inc
try:
    p = Path(agents_inc.__file__).resolve().parent / 'docs' / 'internal' / 'session-intake.md'
    print('session intake doc:', p)
except Exception:
    pass
PY

python3 -m agents_inc.cli.init_session
