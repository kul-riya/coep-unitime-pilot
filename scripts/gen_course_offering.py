"""Generate courseOffering.xml from the Taasika snapshot.

Lec and Lab/Tut subjects that share a base shortName are merged into a
single UniTime offering with two subparts.  Within that offering:

* the controlling ``<course>`` is created from the Lec subject;
* the Lec subpart's minPerWeek is ``lec.eachSlot * lec.nSlots * 60``;
* the Lab subpart's minPerWeek is ``lab.eachSlot * lab.nSlots * 60``;
* one Lec ``<class>`` is created per Taasika class (subjectClassTeacher);
* one Lab ``<class>`` is created per Taasika batch (subjectBatchTeacher);
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
# Use "insert" for a fresh UniTime session; "update" when re-importing offerings
# that already exist (matched by offering id / external id).
OFFERING_ACTION = "insert"
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent


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


def _class_id(area: str, course_nbr: str, kind: str, suffix: int) -> str:
    # Prefer short code on the timetable label: "CN Lec 1" not "CS 109 Lec 1".
    return f"{course_nbr} {kind} {suffix}"


def _mapping_rows(
    subj: dict | None,
    sct_by_subject: Dict[int, List[dict]],
    sbt_by_subject: Dict[int, List[dict]],
    *,
    prefer_batch: bool,
) -> tuple[list[dict], list[dict]]:
    """Return (class_rows, batch_rows) for a subject.

    Lec sections normally come from subjectClassTeacher; batch-registered
    electives (DE/Honor/PSEC) put their lecture batches in subjectBatchTeacher
    instead.  Lab sections normally come from subjectBatchTeacher, but some
    M.Tech labs (e.g. MT-GAN-Lab) are registered via subjectClassTeacher.
    """
    if not subj:
        return [], []
    sid = subj["subjectId"]
    sct = sct_by_subject.get(sid, [])
    sbt = sbt_by_subject.get(sid, [])
    if prefer_batch:
        if sbt:
            return [], sbt
        return sct, []
    if sct:
        return sct, []
    if subj.get("batches"):
        return [], sbt
    return sct, sbt


def _build_lec_sections(
    lec_subj: dict | None,
    sct_by_subject: Dict[int, List[dict]],
    sbt_by_subject: Dict[int, List[dict]],
    classes: dict,
    batches: dict,
) -> List[dict]:
    if not lec_subj:
        return []
    sct_rows, sbt_rows = _mapping_rows(
        lec_subj, sct_by_subject, sbt_by_subject, prefer_batch=False
    )
    sections: List[dict] = []
    for row in sct_rows:
        cls = classes.get(row["classId"])
        if not cls:
            continue
        sections.append(
            {
                "row": row,
                "limit": cls["classCount"] or 0,
                "schedule_note": cls["classShortName"],
                "via": "class",
                "class": cls,
                "batch": None,
            }
        )
    for row in sbt_rows:
        batch = batches.get(row["batchId"])
        if not batch:
            continue
        sections.append(
            {
                "row": row,
                "limit": batch["batchCount"] or 0,
                "schedule_note": batch["batchName"],
                "via": "batch",
                "class": None,
                "batch": batch,
            }
        )
    return sections


def _build_lab_sections(
    lab_subj: dict | None,
    sct_by_subject: Dict[int, List[dict]],
    sbt_by_subject: Dict[int, List[dict]],
    classes: dict,
    batches: dict,
) -> List[dict]:
    if not lab_subj:
        return []
    sct_rows, sbt_rows = _mapping_rows(
        lab_subj, sct_by_subject, sbt_by_subject, prefer_batch=True
    )
    sections: List[dict] = []
    for row in sbt_rows:
        batch = batches.get(row["batchId"])
        if not batch:
            continue
        sections.append(
            {
                "row": row,
                "limit": batch["batchCount"] or 0,
                "schedule_note": batch["batchName"],
                "via": "batch",
                "class": None,
                "batch": batch,
            }
        )
    for row in sct_rows:
        cls = classes.get(row["classId"])
        if not cls:
            continue
        sections.append(
            {
                "row": row,
                "limit": cls["classCount"] or 0,
                "schedule_note": cls["classShortName"],
                "via": "class",
                "class": cls,
                "batch": None,
            }
        )
    return sections


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
    lec_to_lab: dict[int, int] = pairs["lec_to_lab"]
    lab_to_lec: dict[int, int] = pairs["lab_to_lec"]

    subject_idx: dict[str, dict] = json.loads(
        (SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8")
    )

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

    for primary in subjects:
        sid = primary["subjectId"]
        if sid in lab_to_lec:
            continue

        info = subject_idx.get(str(sid))
        if not info:
            continue

        # A subject counts as "lab-only" (no lecture) only when it is batch-
        # registered AND classifications.find_course_pairs could not find a
        # lecture partner for it. Do NOT infer this from the raw ``batches``
        # flag alone: elective lectures (DE/Honor/PSEC/MDM) are also batch-
        # registered in Taasika, so a paired lecture (sid in lec_to_lab) must
        # still be treated as the Lec subpart even though batches is set.
        is_lab_only = bool(primary.get("batches")) and sid not in lec_to_lab
        lec_subj: dict | None = None if is_lab_only else primary
        lab_subj: dict | None = None
        if sid in lec_to_lab:
            lab_subj = subj_by_id.get(lec_to_lab[sid])
        elif is_lab_only:
            lab_subj = primary

        lec_sections = _build_lec_sections(
            lec_subj, sct_by_subject, sbt_by_subject, classes, batches
        )
        lab_sections = _build_lab_sections(
            lab_subj, sct_by_subject, sbt_by_subject, classes, batches
        )

        if not lec_sections and not lab_sections:
            skipped_no_mappings.append(f"{sid}:{primary['subjectShortName']}")
            continue

        config_limit = sum(entry["limit"] for entry in lec_sections + lab_sections)
        if config_limit == 0:
            config_limit = 30

        area = info["subjectArea"]
        course_nbr = info["courseNumber"]
        title = info["title"]

        lec_min_per_week = 0
        if lec_subj and lec_sections:
            lec_min_per_week = (lec_subj.get("eachSlot") or 0) * (lec_subj.get("nSlots") or 0) * 60
        lab_min_per_week = 0
        if lab_subj and lab_sections:
            lab_min_per_week = (lab_subj.get("eachSlot") or 0) * (lab_subj.get("nSlots") or 0) * 60

        used_offering_ids.append(sid)
        lines.append(f'  <offering id="{sid}" offered="true" action="{OFFERING_ACTION}">')
        lines.append(
            f'    <course id="{sid}" subject="{xml_escape(area)}" '
            f'courseNbr="{xml_escape(course_nbr)}" controlling="true" '
            f'title="{xml_escape(title)}" '
            f'scheduleBookNote="{xml_escape(course_nbr)}"/>'
        )
        lines.append(f'    <config name="1" limit="{config_limit}">')
        if lec_min_per_week > 0 and lec_sections:
            lines.append(f'      <subpart type="Lec" suffix="" minPerWeek="{lec_min_per_week}"/>')
        if lab_min_per_week > 0 and lab_sections:
            lines.append(f'      <subpart type="Lab" suffix="" minPerWeek="{lab_min_per_week}"/>')

        for idx, entry in enumerate(lec_sections, start=1):
            row = entry["row"]
            cid = _class_id(area, course_nbr, "Lec", idx)
            room_refs: List[dict] = []
            for sr in subject_rooms.get(lec_subj["subjectId"], [])[:1]:
                room = rooms.get(sr["roomId"])
                if room:
                    room_refs.append(room)
            if entry["via"] == "class":
                cls = entry["class"]
                for cr in class_rooms_by_class.get(cls["classId"], [])[:1]:
                    room = rooms.get(cr["roomId"])
                    if room and (not room_refs or room["roomId"] != room_refs[0]["roomId"]):
                        room_refs.append(room)
                offset_key = (lec_subj["subjectId"], f"Lec-class-{cls['classId']}")
            else:
                batch = entry["batch"]
                for br in batch_rooms_by_batch.get(batch["batchId"], [])[:1]:
                    room = rooms.get(br["roomId"])
                    if room and (not room_refs or room["roomId"] != room_refs[0]["roomId"]):
                        room_refs.append(room)
                offset_key = (lec_subj["subjectId"], f"Lec-batch-{batch['batchId']}")
            _emit_class(
                lines,
                cid,
                "Lec",
                idx,
                entry["limit"],
                entry["schedule_note"],
                room_refs,
                row.get("teacherId"),
            )
            section_offset[offset_key] = idx

        for idx, entry in enumerate(lab_sections, start=1):
            row = entry["row"]
            cid = _class_id(area, course_nbr, "Lab", idx)
            room_refs = []
            for sr in subject_rooms.get(lab_subj["subjectId"], [])[:1]:
                room = rooms.get(sr["roomId"])
                if room:
                    room_refs.append(room)
            if entry["via"] == "batch":
                batch = entry["batch"]
                for br in batch_rooms_by_batch.get(batch["batchId"], [])[:1]:
                    room = rooms.get(br["roomId"])
                    if room and (not room_refs or room["roomId"] != room_refs[0]["roomId"]):
                        room_refs.append(room)
                offset_key = (lab_subj["subjectId"], f"Lab-batch-{batch['batchId']}")
            else:
                cls = entry["class"]
                for cr in class_rooms_by_class.get(cls["classId"], [])[:1]:
                    room = rooms.get(cr["roomId"])
                    if room and (not room_refs or room["roomId"] != room_refs[0]["roomId"]):
                        room_refs.append(room)
                offset_key = (lab_subj["subjectId"], f"Lab-class-{cls['classId']}")
            _emit_class(
                lines,
                cid,
                "Lab",
                idx,
                entry["limit"],
                entry["schedule_note"],
                room_refs,
                row.get("teacherId"),
            )
            section_offset[offset_key] = idx

        lines.append("    </config>")
        lines.append("  </offering>")
        offering_records.append((sid, lab_subj["subjectId"] if lab_subj else None))

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

    extra = {
        "offerings": used_offering_ids,
        "section_offsets": {f"{k[0]}|{k[1]}": v for k, v in section_offset.items()},
        "lec_to_lab": {str(k): v for k, v in lec_to_lab.items()},
        "skipped_subjects": skipped_no_mappings,
    }
    (SCRIPTS_DIR / "offering_index.json").write_text(json.dumps(extra), encoding="utf-8")


if __name__ == "__main__":
    main()
