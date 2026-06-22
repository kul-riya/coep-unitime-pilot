"""Generate preferences.xml with time/date patterns for every schedulable subpart.

UniTime's course timetabling solver requires each class to have a time pattern
before it can be loaded.  ``courseOffering.xml`` defines minutes/week on
subparts but not patterns; this file fills that gap via the Preferences XML
import (Administration > Academic Sessions > Data Exchange).

Reference: https://www.unitime.org/interface/preferences.xml
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from xml_common import LICENSE_HEADER, xml_escape


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
DATE_PATTERN = "Full Term"


def _time_pattern(subpart_type: str, min_per_week: int) -> str:
    """Map subpart duration to a sessionSetup time pattern name."""
    if min_per_week == 60:
        return "1 x 60"
    if min_per_week == 120:
        return "1 x 120" if subpart_type == "Lab" else "2 x 60"
    if min_per_week == 180:
        return "1 x 180" if subpart_type == "Lab" else "3 x 60"
    if min_per_week == 300:
        return "5 x 60"
    raise ValueError(
        f"no time pattern for {subpart_type} with minPerWeek={min_per_week}"
    )


def main() -> None:
    src = OUT_DIR / "courseOffering.xml"
    root = ET.parse(src).getroot()

    lines: list[str] = [
        LICENSE_HEADER,
        f'<preferences campus="{CAMPUS}" term="{TERM}" year="{YEAR}" '
        f'dateFormat="yyyy/M/d" timeFormat="HHmm" '
        f'created="Generated from courseOffering.xml">',
    ]

    subpart_count = 0
    class_count = 0

    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue
        subject = course.get("subject", "")
        course_nbr = course.get("courseNbr", "")

        for config in offering.findall("config"):
            config_name = config.get("name", "1")
            subparts = {
                sp.get("type", ""): sp
                for sp in config.findall("subpart")
            }
            classes_by_type: dict[str, list[ET.Element]] = {}
            for cls in config.findall("class"):
                if cls.get("cancelled", "false").lower() == "true":
                    continue
                classes_by_type.setdefault(cls.get("type", ""), []).append(cls)

            for sp_type, sp in subparts.items():
                if not sp_type:
                    continue
                mins = int(sp.get("minPerWeek", "0") or 0)
                if mins <= 0:
                    continue
                pattern = _time_pattern(sp_type, mins)
                suffix = sp.get("suffix") or ""
                subpart_count += 1

                lines.append(
                    f'  <subpart subject="{xml_escape(subject)}" '
                    f'course="{xml_escape(course_nbr)}" '
                    f'config="{xml_escape(config_name)}" '
                    f'type="{xml_escape(sp_type)}"'
                    + (f' suffix="{xml_escape(suffix)}"' if suffix else "")
                    + ">"
                )
                lines.append(f'    <timePref pattern="{pattern}" level="R"/>')
                lines.append(f'    <datePref pattern="{DATE_PATTERN}" level="R"/>')
                lines.append("  </subpart>")

                for cls in classes_by_type.get(sp_type, []):
                    cls_suffix = cls.get("suffix", "")
                    if not cls_suffix:
                        continue
                    class_count += 1
                    lines.append(
                        f'  <class subject="{xml_escape(subject)}" '
                        f'course="{xml_escape(course_nbr)}" '
                        f'type="{xml_escape(sp_type)}" '
                        f'suffix="{xml_escape(cls_suffix)}"/>'
                    )

    lines.append("</preferences>\n")

    out = OUT_DIR / "preferences.xml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} "
        f"({out.stat().st_size:,} bytes, {subpart_count} subparts, {class_count} classes)"
    )


if __name__ == "__main__":
    main()
