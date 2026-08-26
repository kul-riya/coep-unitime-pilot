"""Validate courseOffering.xml structure before UniTime import."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFF = ROOT / "unitime-out" / "courseOffering.xml"


def main() -> int:
    if not OFF.is_file():
        print(f"ERROR: {OFF} not found", file=sys.stderr)
        return 1
    root = ET.parse(OFF).getroot()
    if root.get("incremental", "").lower() != "true":
        print(
            "WARN: root <offerings> should have incremental=\"true\" on sessions "
            "with existing offerings (avoids deleteUnmatchedInstructionalOfferings flush bug)"
        )
    issues: list[str] = []
    class_ids: dict[str, str] = {}

    for off in root.findall("offering"):
        oid = off.get("id", "?")
        course = off.find("course")
        cn = course.get("courseNbr") if course is not None else "?"
        if course is not None and course.find("courseCredit") is None:
            issues.append(f"offering {oid} ({cn}): missing <courseCredit> on controlling course")
        action = off.get("action", "")
        if action not in ("insert", "update", "delete", "create-if-not-exists"):
            issues.append(f"offering {oid} ({cn}): unexpected action={action!r}")

        for cfg in off.findall("config"):
            subparts = {sp.get("type") for sp in cfg.findall("subpart")}
            classes_by_type: dict[str, int] = {}
            for c in cfg.findall("class"):
                typ = c.get("type", "")
                classes_by_type[typ] = classes_by_type.get(typ, 0) + 1
                cid = c.get("id", "")
                if cid in class_ids:
                    issues.append(
                        f"duplicate class id {cid!r}: {class_ids[cid]} and offering {oid} ({cn})"
                    )
                else:
                    class_ids[cid] = f"offering {oid} ({cn})"
            for typ in subparts:
                if classes_by_type.get(typ, 0) == 0:
                    issues.append(f"offering {oid} ({cn}): subpart {typ} with no {typ} classes")
            for typ, n in classes_by_type.items():
                if typ not in subparts:
                    issues.append(f"offering {oid} ({cn}): {n} {typ} class(es) without {typ} subpart")

    print(f"Validated {len(root.findall('offering'))} offerings, {len(class_ids)} classes")
    if issues:
        print(f"FAIL: {len(issues)} issue(s)")
        for line in issues[:30]:
            print(f"  - {line}")
        return 1
    print("OK: courseOffering.xml structure looks valid for UniTime import")
    return 0


if __name__ == "__main__":
    sys.exit(main())
