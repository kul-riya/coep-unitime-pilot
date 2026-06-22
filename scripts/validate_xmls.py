"""Quick well-formedness check on every generated UniTime XML file."""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET


OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"


def main() -> int:
    failures: list[tuple[str, str]] = []
    files = sorted(OUT_DIR.glob("*.xml"))
    print(f"Validating {len(files)} XML files in {OUT_DIR}...")
    for path in files:
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            count = len(list(root))
            print(f"  OK  {path.name:<28} root=<{root.tag}> children={count}")
        except ET.ParseError as e:
            failures.append((path.name, str(e)))
            print(f"  FAIL {path.name}: {e}")
    if failures:
        print(f"\n{len(failures)} file(s) failed parsing.")
        return 1
    print("\nAll files parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
