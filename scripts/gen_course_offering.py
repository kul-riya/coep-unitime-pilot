"""Generate courseOffering.xml from the Taasika snapshot.

B.Tech subjects are scaled to 5 lecture divisions (100 students each)
and 20 lab batches (25 students each, 4 per division).  M.Tech subjects
keep their Taasika section counts with adjusted limits.

Within each offering:

* the controlling ``<course>`` is created from the Lec subject;
* the Lec subpart's minPerWeek is ``lec.eachSlot * lec.nSlots * 60``;
* every lab meeting is a two-hour block; requirements above two hours are
  represented as two weekly meetings (four hours total);
* each ``<class>`` carries ``studentScheduling="true"``,
  ``displayInScheduleBook="true"`` and ``cancelled="false"``;
* class ids are human-readable strings like ``CS 207 Lab 3`` so they appear
  cleanly in the UniTime UI.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from classifications import find_course_pairs


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent

# Target section sizes for B.Tech year subjects
BTECH_DIVS = 5                 # 5 divisions (100 students each)
BTECH_BATCHES_PER_DIV = 4      # 4 batches per division (25 students each)
BTECH_LEC_LIMIT = 100          # students per lecture section
BTECH_LAB_LIMIT = 25           # students per lab section

EXCLUDED_ROOM_SHORT_NAMES = {
    "Cogni-34",
    "Unavail-A",
    "Unavail-B",
    "Unavail-C",
    "Unavail-D",
}

SUPPLEMENTAL_CSE_LABS: List[dict] = [
    {
        "roomId": f"new-cse-lab-f{floor}-{lab:02d}",
        "roomName": f"New CSE Building, Floor {floor}, CSE Lab {lab:02d}",
        "roomShortName": f"CSE-F{floor}-L{lab:02d}",
            "roomCount": 25,
        "snapshotId": 240,
    }
    for floor in range(1, 4)
    for lab in range(1, 7)
]


def _building_for(room_name: str, room_short: str) -> str:
    name = (room_name or "").lower()
    short = (room_short or "").lower()
    if "academic complex" in name or "acadmie" in name or "acadmic" in name:
        return "AC"
    if "new cse building" in name:
        return "NCSE"
    if "bhau" in name:
        return "BHAU"
    if "online" in name:
        return "ONL"
    if "lab-unavailable" in name or "unavail" in short:
        return "UNAV"
    if "entc ext" in name or short.startswith("cet") or "sh entc" in name or short == "sh":
        return "ENTCX"
    return "CSED"


def _room_number(room_short: str) -> str:
    short = (room_short or "").strip()
    cleaned = re.sub(r"[()\s]+", "", short)
    return cleaned.strip("_-") or "x"


def _is_excluded_room(room: dict) -> bool:
    short = (room.get("roomShortName") or "").strip()
    name = (room.get("roomName") or "").lower()
    return short in EXCLUDED_ROOM_SHORT_NAMES or short.lower().startswith("unavail") or "unavailable" in name


def _append_room_ref(room_refs: List[dict], room: dict | None) -> None:
    if room is None or _is_excluded_room(room):
        return
    if not any(existing["roomId"] == room["roomId"] for existing in room_refs):
        room_refs.append(room)


def _append_supplemental_cse_labs(room_refs: List[dict]) -> None:
    for room in SUPPLEMENTAL_CSE_LABS:
        _append_room_ref(room_refs, room)


def _class_id(area: str, course_nbr: str, kind: str, suffix: int) -> str:
    return f"{area} {course_nbr} {kind} {suffix}"


def _emit_class(
    lines: List[str],
    class_id: str,
    kind: str,
    suffix: int,
    limit: int,
    schedule_note: str,
    room_refs: List[dict],
    instructor_id: int | None,
) -> None:
    lines.append(
        f'      <class id="{xml_escape(class_id)}" type="{kind}" suffix="{suffix}" '
        f'limit="{limit}" scheduleNote="{xml_escape(schedule_note)}" '
        f'studentScheduling="true" displayInScheduleBook="true" cancelled="false">'
    )
    for r in room_refs:
        lines.append(
            f'        <room id="taasika-room-{r["roomId"]}" '
            f'building="{_building_for(r["roomName"], r["roomShortName"])}" '
            f'roomNbr="{xml_escape(_room_number(r["roomShortName"]))}"/>'
        )
    if instructor_id is not None:
        lines.append(
            f'        <instructor id="taasika-teacher-{instructor_id}" '
            f'share="100" lead="true"/>'
        )
    lines.append("      </class>")


def main() -> None:
    data = load(
        snapshot_id=240,
        tables=[
            "subject",
            "class",
            "batch",
            "batchClass",
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
    rooms = {
        r["roomId"]: r
        for r in data.filtered("room")
        if not _is_excluded_room(r)
    }

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
    lec_to_lab: dict[int, int] = pairs["lec_to_lab"]
    lab_to_lec: dict[int, int] = pairs["lab_to_lec"]

    subject_idx: dict[str, dict] = json.loads(
        (SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8")
    )

    # --- Build batch -> parent class mapping from the batchClass table ---
    batch_to_class: Dict[int, int] = {}
    for row in data.filtered("batchClass"):
        batch_to_class[row["batchId"]] = row["classId"]

    lines: List[str] = [LICENSE_HEADER]
    lines.append(
        f'<offerings campus="{CAMPUS}" year="{YEAR}" term="{TERM}" '
        f'dateFormat="yyyy/M/d" timeFormat="HHmm" '
        f'created="Generated from Taasika snapshot 240" includeExams="none">'
    )

    offering_records: List[tuple[int, int | None]] = []
    section_offset: Dict[tuple[int, str], int] = {}
    skipped_no_mappings: List[str] = []
    used_offering_ids: List[int] = []
    parent_child_map: Dict[str, Dict[str, List[int]]] = {}

    for primary in subjects:
        sid = primary["subjectId"]
        if sid in lab_to_lec:
            continue

        info = subject_idx.get(str(sid))
        if not info:
            continue

        lec_subj: dict | None = primary if not primary.get("batches") else None
        lab_subj: dict | None = None
        if sid in lec_to_lab:
            lab_subj = subj_by_id.get(lec_to_lab[sid])
        elif primary.get("batches"):
            lab_subj = primary
            lec_subj = None

        lec_rows = sct_by_subject.get(lec_subj["subjectId"], []) if lec_subj else []
        lab_rows = sbt_by_subject.get(lab_subj["subjectId"], []) if lab_subj else []

        if not lec_rows and not lab_rows:
            skipped_no_mappings.append(f"{sid}:{primary['subjectShortName']}")
            continue

        # --- Determine subject area and metadata ---
        area = info["subjectArea"]
        course_nbr = info["courseNumber"]
        title = info["title"]

        lec_min_per_week = 0
        if lec_subj:
            lec_min_per_week = (lec_subj.get("eachSlot") or 0) * (lec_subj.get("nSlots") or 0) * 60
        lab_min_per_week = 0
        if lab_subj:
            source_lab_minutes = (lab_subj.get("eachSlot") or 0) * (lab_subj.get("nSlots") or 0) * 60
            # Local curriculum rule: each lab meeting is exactly two hours.
            # A source requirement above two hours is represented by two
            # two-hour meetings (four hours per week).
            lab_min_per_week = 120 if source_lab_minutes <= 120 else 240

        # --- Gather Taasika sections for instructor/room cycling ---
        lec_sections: List[dict] = []
        for row in lec_rows:
            cls = classes.get(row["classId"])
            if not cls:
                continue
            lec_sections.append({"row": row, "class": cls})

        lab_sections: List[dict] = []
        for row in lab_rows:
            batch = batches.get(row["batchId"])
            if not batch:
                continue
            lab_sections.append({"row": row, "batch": batch})

        has_lec = bool(lec_subj and lec_min_per_week > 0 and lec_sections)
        has_lab = bool(lab_subj and lab_min_per_week > 0 and lab_sections)

        if not has_lec and not has_lab:
            skipped_no_mappings.append(f"{sid}:{primary['subjectShortName']}(no-sections)")
            continue

        # --- Determine target section counts ---
        is_mtech = (area == "MT")

        if is_mtech:
            # M.Tech: keep Taasika section counts with adjusted limits
            n_lec = len(lec_sections) if has_lec else 0
            n_lab_total = len(lab_sections) if has_lab else 0
            n_lab_per_lec = max(1, n_lab_total // max(n_lec, 1)) if n_lab_total and n_lec else n_lab_total
            lec_limit = 60
            lab_limit = 25
        else:
            # B.Tech: scale to 5 divisions, 25 batches
            n_lec = BTECH_DIVS if has_lec else 0
            n_lab_per_lec = BTECH_BATCHES_PER_DIV if has_lab else 0
            n_lab_total = (n_lec * n_lab_per_lec) if n_lec > 0 else (
                BTECH_DIVS * BTECH_BATCHES_PER_DIV if has_lab else 0
            )
            lec_limit = BTECH_LEC_LIMIT
            lab_limit = BTECH_LAB_LIMIT

        config_limit = max(n_lec * lec_limit, n_lab_total * lab_limit, 30)

        # --- Emit offering header ---
        used_offering_ids.append(sid)
        lines.append(f'  <offering id="{sid}" offered="true" action="update">')
        lines.append(
            f'    <course id="{sid}" subject="{xml_escape(area)}" '
            f'courseNbr="{xml_escape(course_nbr)}" controlling="true" '
            f'title="{xml_escape(title)}" scheduleBookNote=""/>'
        )
        lines.append(f'    <config name="1" limit="{config_limit}">')

        # --- Emit subparts: nest Lab inside Lec when both exist ---
        if has_lec and has_lab and n_lec > 0 and n_lab_total > 0:
            lines.append(f'      <subpart type="Lec" suffix="" minPerWeek="{lec_min_per_week}">')
            lines.append(f'        <subpart type="Lab" suffix="" minPerWeek="{lab_min_per_week}"/>')
            lines.append("      </subpart>")
        elif has_lec and n_lec > 0:
            lines.append(f'      <subpart type="Lec" suffix="" minPerWeek="{lec_min_per_week}"/>')
        elif has_lab and n_lab_total > 0:
            lines.append(f'      <subpart type="Lab" suffix="" minPerWeek="{lab_min_per_week}"/>')

        # --- Emit sections ---
        offering_pc: Dict[int, List[int]] = {}

        if n_lec > 0 and has_lec:
            for lec_idx in range(1, n_lec + 1):
                # Cycle through Taasika data for instructor/room
                src_lec = lec_sections[(lec_idx - 1) % len(lec_sections)]
                src_cls = src_lec["class"]
                src_row = src_lec["row"]
                teacher_id = src_row.get("teacherId")
                schedule_note = f"Div{lec_idx}"

                room_refs: List[dict] = []
                for sr in subject_rooms.get(lec_subj["subjectId"], [])[:1]:
                    _append_room_ref(room_refs, rooms.get(sr["roomId"]))
                for cr in class_rooms_by_class.get(src_cls["classId"], [])[:1]:
                    _append_room_ref(room_refs, rooms.get(cr["roomId"]))

                cid = _class_id(area, course_nbr, "Lec", lec_idx)

                if has_lab and n_lab_per_lec > 0:
                    # Lec with nested Lab children
                    lines.append(
                        f'      <class id="{xml_escape(cid)}" type="Lec" suffix="{lec_idx}" '
                        f'limit="{lec_limit}" scheduleNote="{xml_escape(schedule_note)}" '
                        f'studentScheduling="true" displayInScheduleBook="true" cancelled="false">'
                    )
                    for r in room_refs:
                        lines.append(
                            f'        <room id="taasika-room-{r["roomId"]}" '
                            f'building="{_building_for(r["roomName"], r["roomShortName"])}" '
                            f'roomNbr="{xml_escape(_room_number(r["roomShortName"]))}"/>'
                        )
                    if teacher_id is not None:
                        lines.append(
                            f'        <instructor id="taasika-teacher-{teacher_id}" '
                            f'share="100" lead="true"/>'
                        )

                    child_suffixes: List[int] = []
                    for batch_in_div in range(1, n_lab_per_lec + 1):
                        lab_global_idx = (lec_idx - 1) * n_lab_per_lec + batch_in_div
                        src_lab = lab_sections[(lab_global_idx - 1) % len(lab_sections)]
                        src_batch = src_lab["batch"]
                        src_lab_row = src_lab["row"]
                        lab_teacher_id = src_lab_row.get("teacherId")
                        lab_note = f"Div{lec_idx}-B{batch_in_div}"

                        lab_room_refs: List[dict] = []
                        for sr in subject_rooms.get(lab_subj["subjectId"], [])[:1]:
                            _append_room_ref(lab_room_refs, rooms.get(sr["roomId"]))
                        for br in batch_rooms_by_batch.get(src_batch["batchId"], [])[:1]:
                            _append_room_ref(lab_room_refs, rooms.get(br["roomId"]))
                        _append_supplemental_cse_labs(lab_room_refs)

                        lab_cid = _class_id(area, course_nbr, "Lab", lab_global_idx)
                        lines.append(
                            f'        <class id="{xml_escape(lab_cid)}" type="Lab" suffix="{lab_global_idx}" '
                            f'limit="{lab_limit}" scheduleNote="{xml_escape(lab_note)}" '
                            f'studentScheduling="true" displayInScheduleBook="true" cancelled="false">'
                        )
                        for r in lab_room_refs:
                            lines.append(
                                f'          <room id="taasika-room-{r["roomId"]}" '
                                f'building="{_building_for(r["roomName"], r["roomShortName"])}" '
                                f'roomNbr="{xml_escape(_room_number(r["roomShortName"]))}"/>'
                            )
                        if lab_teacher_id is not None:
                            lines.append(
                                f'          <instructor id="taasika-teacher-{lab_teacher_id}" '
                                f'share="100" lead="true"/>'
                            )
                        lines.append("        </class>")

                        section_offset[(lab_subj["subjectId"], f"Lab-sec-{lab_global_idx}")] = lab_global_idx
                        child_suffixes.append(lab_global_idx)

                    lines.append("      </class>")
                    offering_pc[lec_idx] = child_suffixes
                else:
                    # Lec without Lab children
                    _emit_class(
                        lines, cid, "Lec", lec_idx, lec_limit,
                        schedule_note, room_refs, teacher_id,
                    )

                section_offset[(lec_subj["subjectId"], f"Lec-div-{lec_idx}")] = lec_idx

        # --- Orphan Labs (lab-only offerings, no Lec) ---
        if n_lec == 0 and n_lab_total > 0 and has_lab:
            for lab_idx in range(1, n_lab_total + 1):
                src_lab = lab_sections[(lab_idx - 1) % len(lab_sections)]
                src_batch = src_lab["batch"]
                src_lab_row = src_lab["row"]
                lab_teacher_id = src_lab_row.get("teacherId")
                lab_note = f"B{lab_idx}"

                room_refs: List[dict] = []
                for sr in subject_rooms.get(lab_subj["subjectId"], [])[:1]:
                    _append_room_ref(room_refs, rooms.get(sr["roomId"]))
                for br in batch_rooms_by_batch.get(src_batch["batchId"], [])[:1]:
                    _append_room_ref(room_refs, rooms.get(br["roomId"]))
                _append_supplemental_cse_labs(room_refs)

                cid = _class_id(area, course_nbr, "Lab", lab_idx)
                _emit_class(
                    lines, cid, "Lab", lab_idx, lab_limit,
                    lab_note, room_refs, lab_teacher_id,
                )
                section_offset[(lab_subj["subjectId"], f"Lab-sec-{lab_idx}")] = lab_idx

        lines.append("    </config>")
        lines.append("  </offering>")
        offering_records.append((sid, lab_subj["subjectId"] if lab_subj else None))
        if offering_pc:
            parent_child_map[str(sid)] = {str(k): v for k, v in offering_pc.items()}

    lines.append("</offerings>\n")

    out = OUT_DIR / "courseOffering.xml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} ({out.stat().st_size:,} bytes, "
        f"{len(used_offering_ids)} offerings)"
    )
    if skipped_no_mappings:
        print(
            f"skipped {len(skipped_no_mappings)} primary subjects with no SCT/SBT in snapshot 240 "
            f"(first 5: {', '.join(skipped_no_mappings[:5])})"
        )

    # Count nesting stats
    nested_count = sum(1 for pc in parent_child_map.values() for _ in pc)
    total_lab_children = sum(len(v) for pc in parent_child_map.values() for v in pc.values())
    print(
        f"parent-child nesting: {len(parent_child_map)} offerings, "
        f"{nested_count} Lec parents, {total_lab_children} nested Lab children"
    )

    extra = {
        "offerings": used_offering_ids,
        "section_offsets": {f"{k[0]}|{k[1]}": v for k, v in section_offset.items()},
        "lec_to_lab": {str(k): v for k, v in lec_to_lab.items()},
        "skipped_subjects": skipped_no_mappings,
        "parent_child": parent_child_map,
        "batch_to_class": {str(k): v for k, v in batch_to_class.items()},
    }
    (SCRIPTS_DIR / "offering_index.json").write_text(json.dumps(extra), encoding="utf-8")


if __name__ == "__main__":
    main()
