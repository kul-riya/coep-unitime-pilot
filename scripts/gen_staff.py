"""Generate staff.xml from the Taasika teacher table."""

from __future__ import annotations

import re
from pathlib import Path

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from classifications import department_code


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"


_ADJUNCT_NAME_RE = re.compile(r"\s*\(?\s*Adjunct\s*\)?\s*$", re.I)


def _position_type(min_hrs: int | None, max_hrs: int | None, forced: str | None = None) -> str:
    """Pick a UniTime ``positionType`` from a teacher's load envelope.

    ``ADJUNCT`` is the UniTime code whose UI label is **Adjunct Faculty**.
    Do not put that phrase in the instructor's name.
    """
    if forced:
        return forced
    if (min_hrs or 0) == 0 and (max_hrs or 0) == 0:
        return "ADJUNCT"
    if (min_hrs or 0) == 0 and (max_hrs or 0) >= 24:
        return "VISITOR"
    if (min_hrs or 0) <= 6:
        return "PROF"
    if (min_hrs or 0) <= 12:
        return "ASSOC_PROF"
    if (min_hrs or 0) <= 14:
        return "ASST_PROF"
    return "ASST_PROF"


def _clean_display_name(full_name: str) -> tuple[str, str | None]:
    """Strip position markers from the name; return (name, forced positionType)."""
    name = (full_name or "").strip()
    forced: str | None = None
    if _ADJUNCT_NAME_RE.search(name):
        name = _ADJUNCT_NAME_RE.sub("", name).strip()
        forced = "ADJUNCT"
    if name.lower().startswith("visiting "):
        name = name[9:].strip()
        forced = forced or "VISITOR"
    return name, forced


def _split_name(full_name: str) -> tuple[str, str, str]:
    parts = re.split(r"\s+", (full_name or "").strip())
    if not parts:
        return ("", "", "")
    if len(parts) == 1:
        return (parts[0], "", "")
    if len(parts) == 2:
        return (parts[0], "", parts[1])
    return (parts[0], " ".join(parts[1:-1]), parts[-1])


def main() -> None:
    data = load(snapshot_id=240, tables=["teacher"])
    teachers = sorted(data.filtered("teacher"), key=lambda t: t["teacherId"])

    lines: list[str] = [LICENSE_HEADER]
    lines.append(f'<staff campus="{CAMPUS}" term="{TERM}" year="{YEAR}">')
    for t in teachers:
        display, forced_pos = _clean_display_name(t["teacherName"] or "")
        first, middle, last = _split_name(display)
        if not last:
            last = first
            first = t["teacherShortName"] or first
        pos = _position_type(t.get("minHrs"), t.get("maxHrs"), forced_pos)
        dept = department_code(t.get("deptId"))
        short = t["teacherShortName"] or first
        email = f"{re.sub(r'[^A-Za-z0-9]+', '.', short).strip('.').lower()}@unitime.local"
        attrs = [
            f'externalId="taasika-teacher-{t["teacherId"]}"',
            f'firstName="{xml_escape(first)}"',
        ]
        if middle:
            attrs.append(f'middleName="{xml_escape(middle)}"')
        attrs.append(f'lastName="{xml_escape(last)}"')
        attrs.append(f'positionType="{pos}"')
        attrs.append(f'department="{dept}"')
        attrs.append(f'email="{xml_escape(email)}"')
        lines.append(f'  <staffMember {" ".join(attrs)}/>')
    lines.append('</staff>\n')

    out = OUT_DIR / "staff.xml"
    body = "\n".join(lines)
    out.write_text(body, encoding="utf-8")
    (OUT_DIR / "10staff.xml").write_text(body, encoding="utf-8")
    print(f"wrote {out.relative_to(OUT_DIR.parent)} ({out.stat().st_size:,} bytes, {len(teachers)} staff members)")


if __name__ == "__main__":
    main()
