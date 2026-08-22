"""Generate preferences.xml with time/date/room patterns for every schedulable subpart.

UniTime's course timetabling solver requires each class to have a time pattern
before it can be loaded.  ``courseOffering.xml`` defines minutes/week on
subparts but not patterns; this file fills that gap via the Preferences XML
import (Administration > Academic Sessions > Data Exchange).

Room preferences are sourced from all Taasika ``subjectRoom`` / ``classRoom`` /
``batchRoom`` rows (not just the first rooms embedded in courseOffering.xml).

Reference: https://www.unitime.org/interface/preferences.xml
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from classifications import find_course_pairs
from gen_course_offering import _building_for, _room_number
from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent
DATE_PATTERN = "Full Term"

RoomKey = Tuple[str, str]  # (building, roomNbr)


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


def _room_key(room: dict) -> RoomKey:
    building = _building_for(room.get("roomName") or "", room.get("roomShortName") or "")
    nbr = _room_number(room.get("roomShortName") or "")
    return building, nbr


def _collect_class_rooms(snapshot_id: int = 240) -> dict[tuple[str, str, str, str], list[RoomKey]]:
    """(subject, courseNbr, type, suffix) → ordered unique room keys."""
    data = load(
        snapshot_id=snapshot_id,
        tables=[
            "subject",
            "class",
            "batch",
            "room",
            "subjectClassTeacher",
            "subjectBatchTeacher",
            "subjectRoom",
            "classRoom",
            "batchRoom",
        ],
    )
    subjects = sorted(data.filtered("subject"), key=lambda s: s["subjectId"])
    subj_by_id = {s["subjectId"]: s for s in subjects}
    classes = {c["classId"]: c for c in data.filtered("class")}
    batches = {b["batchId"]: b for b in data.filtered("batch")}
    rooms = {r["roomId"]: r for r in data.filtered("room")}

    sct_by_subject: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("subjectClassTeacher"):
        sct_by_subject[row["subjectId"]].append(row)

    sbt_by_subject: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("subjectBatchTeacher"):
        sbt_by_subject[row["subjectId"]].append(row)

    subject_rooms: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("subjectRoom"):
        subject_rooms[row["subjectId"]].append(row)

    class_rooms_by_class: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("classRoom"):
        class_rooms_by_class[row["classId"]].append(row)

    batch_rooms_by_batch: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("batchRoom"):
        batch_rooms_by_batch[row["batchId"]].append(row)

    pairs = find_course_pairs(subjects)
    lec_to_lab = pairs["lec_to_lab"]
    lab_to_lec = pairs["lab_to_lec"]

    subject_idx: dict[str, dict] = json.loads(
        (SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8")
    )

    out: dict[tuple[str, str, str, str], list[RoomKey]] = {}

    def add_rooms(key: tuple[str, str, str, str], room_ids: List[int]) -> None:
        seen: set[RoomKey] = set(out.get(key, []))
        ordered = list(out.get(key, []))
        for rid in room_ids:
            room = rooms.get(rid)
            if not room:
                continue
            rk = _room_key(room)
            if rk not in seen:
                seen.add(rk)
                ordered.append(rk)
        if ordered:
            out[key] = ordered

    for primary in subjects:
        sid = primary["subjectId"]
        if sid in lab_to_lec:
            continue
        info = subject_idx.get(str(sid))
        if not info:
            continue

        lec_subj = primary if not primary.get("batches") else None
        lab_subj = None
        if sid in lec_to_lab:
            lab_subj = subj_by_id.get(lec_to_lab[sid])
        elif primary.get("batches"):
            lab_subj = primary

        lec_rows = sct_by_subject.get(lec_subj["subjectId"], []) if lec_subj else []
        lab_rows = sbt_by_subject.get(lab_subj["subjectId"], []) if lab_subj else []
        if not lec_rows and not lab_rows:
            continue

        area = info["subjectArea"]
        course_nbr = info["courseNumber"]

        for idx, row in enumerate(lec_rows, start=1):
            cls = classes.get(row["classId"])
            if not cls:
                continue
            key = (area, course_nbr, "Lec", str(idx))
            ids: List[int] = [sr["roomId"] for sr in subject_rooms.get(lec_subj["subjectId"], [])]
            ids.extend(cr["roomId"] for cr in class_rooms_by_class.get(cls["classId"], []))
            add_rooms(key, ids)

        for idx, row in enumerate(lab_rows, start=1):
            batch = batches.get(row["batchId"])
            if not batch:
                continue
            key = (area, course_nbr, "Lab", str(idx))
            ids = [sr["roomId"] for sr in subject_rooms.get(lab_subj["subjectId"], [])]
            ids.extend(br["roomId"] for br in batch_rooms_by_batch.get(batch["batchId"], []))
            add_rooms(key, ids)

    return out


def _room_pref_lines(rooms: list[RoomKey]) -> list[str]:
    if not rooms:
        return []
    lines: list[str] = []
    for i, (building, nbr) in enumerate(rooms):
        level = "R" if i == 0 else "P"
        lines.append(
            f'    <roomPref building="{xml_escape(building)}" '
            f'room="{xml_escape(nbr)}" level="{level}"/>'
        )
    return lines


def main() -> None:
    src = OUT_DIR / "courseOffering.xml"
    root = ET.parse(src).getroot()
    class_rooms = _collect_class_rooms()

    lines: list[str] = [
        LICENSE_HEADER,
        f'<preferences campus="{CAMPUS}" term="{TERM}" year="{YEAR}" '
        f'dateFormat="yyyy/M/d" timeFormat="HHmm" '
        f'created="Generated from courseOffering.xml + Taasika room prefs">',
    ]

    subpart_count = 0
    class_count = 0
    room_pref_count = 0

    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue
        subject = course.get("subject", "")
        course_nbr = course.get("courseNbr", "")

        for config in offering.findall("config"):
            config_name = config.get("name", "1")
            subparts = {sp.get("type", ""): sp for sp in config.findall("subpart")}
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
                    rk = (subject, course_nbr, sp_type, cls_suffix)
                    rooms = class_rooms.get(rk, [])
                    # Fallback: rooms already on the class in courseOffering.xml
                    if not rooms:
                        for r in cls.findall("room"):
                            rooms.append((r.get("building", ""), r.get("roomNbr", "")))
                    lines.append(
                        f'  <class subject="{xml_escape(subject)}" '
                        f'course="{xml_escape(course_nbr)}" '
                        f'type="{xml_escape(sp_type)}" '
                        f'suffix="{xml_escape(cls_suffix)}">'
                    )
                    rp = _room_pref_lines(rooms)
                    room_pref_count += len(rp)
                    lines.extend(rp)
                    lines.append("  </class>")

    lines.append("</preferences>\n")

    out = OUT_DIR / "preferences.xml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} "
        f"({out.stat().st_size:,} bytes, {subpart_count} subparts, "
        f"{class_count} classes, {room_pref_count} room prefs)"
    )


if __name__ == "__main__":
    main()
