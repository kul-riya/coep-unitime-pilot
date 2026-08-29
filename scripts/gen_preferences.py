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

from classifications import companion_itype, find_course_pairs, is_honor_subject
from gen_course_offering import SYNTHETIC_LAB_DONOR, _building_for, _room_number
from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from intake import is_mdm_subject
from gen_session_setup import _day_codes_for_meetings, _slot_starts, SLOTS_PER_DAY, SLOT_MIN


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent
DATE_PATTERN = "Full Term"

RoomKey = Tuple[str, str]  # (building, roomNbr)


def _time_pattern(sp_type: str, min_per_week: int) -> str:
    """Map subpart type + minutes/week to a standard UniTime time pattern.
    
    Valid session setup patterns include: 1 x 60, 2 x 60, 3 x 60, 4 x 60, 5 x 60,
    1 x 120, 2 x 120, 1 x 180, 1 x 480 Project, Exact Time.
    """
    if sp_type == "Lec":
        if min_per_week == 240:
            return "2 x 120"
        if min_per_week == 180:
            return "3 x 60"
        elif min_per_week == 120:
            return "2 x 60"
        else:
            return f"{min_per_week // 60} x 60"
    elif sp_type in ("Lab", "Rec"):
        if min_per_week == 480:
            return "1 x 480 Project"
        elif min_per_week == 180:
            return "1 x 180"
        elif min_per_week == 120:
            return "1 x 120"
        elif min_per_week == 60:
            return "1 x 60"
    return "Exact Time"


def _get_time_pref_string(pattern_name: str, is_mdm: bool) -> str | None:
    if " x " not in pattern_name:
        return None
    parts = pattern_name.split(" x ")
    nbr_meetings = int(parts[0])
    mins_per_meeting = int(parts[1].split()[0]) # e.g. "60", "120", "480"
    
    day_codes = _day_codes_for_meetings(nbr_meetings)
    starts = _slot_starts(SLOTS_PER_DAY)
    
    max_start_idx = max(0, SLOTS_PER_DAY - (mins_per_meeting // SLOT_MIN))
    valid_starts = starts[:max_start_idx + 1]
    
    pref_chars = []
    for dcode in day_codes:
        d_list = []
        rem = dcode
        while rem:
            for tok in ("Th", "Su", "M", "T", "W", "F", "S"):
                if rem.startswith(tok):
                    d_list.append(tok)
                    rem = rem[len(tok):]
                    break
        
        for start in valid_starts:
            start_min = int(start[:2]) * 60 + int(start[2:])
            end_min = start_min + mins_per_meeting
            
            # MDM block is exactly Mon & Tue, 16:30 to 18:30
            mdm_start = 16 * 60 + 30
            mdm_end = 18 * 60 + 30
            
            time_overlaps = (start_min < mdm_end) and (end_min > mdm_start)
            day_overlaps = bool(set(d_list) & {'M', 'T'})
            intersects = time_overlaps and day_overlaps
            
            if is_mdm:
                # Require exactly MT starting at 16:30 (pattern must be 2 x 120, so dcode MT and start 1630)
                if dcode == "MT" and start == "1630":
                    pref_chars.append("1")
                else:
                    pref_chars.append("P")
            else:
                # Prevent overlapping with MDM block
                if intersects:
                    pref_chars.append("P")
                else:
                    pref_chars.append("2")
                    
    return "".join(pref_chars)


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
        if is_honor_subject(primary.get("subjectShortName") or ""):
            continue
        info = subject_idx.get(str(sid))
        if not info:
            continue

        is_lab_only = bool(primary.get("batches")) and sid not in lec_to_lab
        lec_subj = None if is_lab_only else primary
        lab_subj = None
        if sid in lec_to_lab:
            lab_subj = subj_by_id.get(lec_to_lab[sid])
        elif is_lab_only:
            lab_subj = primary

        lec_rows = sct_by_subject.get(lec_subj["subjectId"], []) if lec_subj else []
        if lec_subj and not lec_rows:
            lec_rows = sbt_by_subject.get(lec_subj["subjectId"], [])
        lab_rows = sbt_by_subject.get(lab_subj["subjectId"], []) if lab_subj else []
        if lab_subj and not lab_rows:
            lab_rows = sct_by_subject.get(lab_subj["subjectId"], [])
        companion_kind = companion_itype((lab_subj or {}).get("subjectShortName") or "Lab")
        if not lec_rows and not lab_rows and lab_subj:
            # Synthetic AI labs: still emit room prefs from the lab subject's rooms.
            lab_room_ids = [sr["roomId"] for sr in subject_rooms.get(lab_subj["subjectId"], [])]
            if lab_room_ids:
                donor_short = SYNTHETIC_LAB_DONOR.get(lab_subj.get("subjectShortName") or "")
                donor = next(
                    (s for s in subjects if s.get("subjectShortName") == donor_short),
                    None,
                )
                donor_rows = sbt_by_subject.get(donor["subjectId"], []) if donor else []
                area = info["subjectArea"]
                course_nbr = info["courseNumber"]
                for idx, _row in enumerate(donor_rows or [None], start=1):
                    add_rooms((area, course_nbr, companion_kind, str(idx)), lab_room_ids)
            continue
        if not lec_rows and not lab_rows:
            continue

        area = info["subjectArea"]
        course_nbr = info["courseNumber"]

        for idx, row in enumerate(lec_rows, start=1):
            cls = classes.get(row.get("classId"))
            key = (area, course_nbr, "Lec", str(idx))
            ids: List[int] = [sr["roomId"] for sr in subject_rooms.get(lec_subj["subjectId"], [])]
            if cls:
                ids.extend(cr["roomId"] for cr in class_rooms_by_class.get(cls["classId"], []))
            add_rooms(key, ids)

        for idx, row in enumerate(lab_rows, start=1):
            batch = batches.get(row.get("batchId"))
            key = (area, course_nbr, companion_kind, str(idx))
            ids = [sr["roomId"] for sr in subject_rooms.get(lab_subj["subjectId"], [])]
            if batch:
                ids.extend(br["roomId"] for br in batch_rooms_by_batch.get(batch["batchId"], []))
            add_rooms(key, ids)

    return out


def _room_pref_lines(rooms: list[RoomKey]) -> list[str]:
    if not rooms:
        return []
    lines: list[str] = []
    for i, (building, nbr) in enumerate(rooms):
        level = "1" if i == 0 else "-1"
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
                is_mdm = is_mdm_subject(course_nbr)
                pref_string = _get_time_pref_string(pattern, is_mdm)
                if pref_string:
                    lines.append(f'    <timePref pattern="{pattern}">{pref_string}</timePref>')
                else:
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
    (OUT_DIR / "13preferences.xml").write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} "
        f"({out.stat().st_size:,} bytes, {subpart_count} subparts, "
        f"{class_count} classes, {room_pref_count} room prefs)"
    )


if __name__ == "__main__":
    main()
