from __future__ import annotations

import sys

from agents_inc.cli import groups


def main() -> int:
    argv = ["agents-inc groups", "new", *sys.argv[1:]]
    prev = sys.argv
    try:
        sys.argv = argv
        print("warning: 'agents-inc new-group' is deprecated; use 'agents-inc groups new'")
        return groups.main()
    finally:
        sys.argv = prev


if __name__ == "__main__":
    raise SystemExit(main())
