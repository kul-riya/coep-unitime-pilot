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
from classifications import companion_itype, find_course_pairs, is_honor_subject, is_minor_subject, skip_offering
from intake import (
    MDM_BLOCK_SEATS,
    MDM_LEC_MIN_PER_WEEK,
    N_DE2_OPTIONS,
    N_DE4_OPTIONS,
    OE_BLOCK_SEATS,
    OE_LEC_MIN_PER_WEEK,
    even_split,
    is_de_subject,
    is_mdm_subject,
    is_oe_subject,
    spread_demand,
    year_from_notes,
    year_headcount,
)


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
# Use "insert" for a fresh UniTime session; "update" when re-importing offerings
# that already exist (matched by offering id / external id).
# Re-import onto a saved timetable must stay on "insert" + incremental="true":
# action="update" hits SchedulingSubpart.itype null on this UniTime build.
OFFERING_ACTION = "insert"
# Required on sessions that already have rolled-forward or partial offerings.
# Without incremental="true", UniTime runs deleteUnmatchedInstructionalOfferings()
# after import and can hit Hibernate TransientObjectException when flushing deletes.
OFFERING_INCREMENTAL = True
# UniTime expects instructional-offering and course external ids to differ
# (see offeringsImportExample.xml: offering id != course id). Re-using the
# same numeric id for both caused Hibernate TransientObjectException on import.
# Room refs stay in preferences.xml. Instructors ARE emitted on classes so the
# solver / CSV export has a lead instructor (staff.xml must already be imported
# and Manage Instructor List run). Earlier TransientObjectException work had
# this off, which left every timetable cell with a blank INSTRUCTOR column.
EMIT_CLASS_ROOMS = False
EMIT_CLASS_INSTRUCTORS = True
# When a paired lab subject has no SCT/SBT (AI-Lab in snapshot 240), clone
# lab batches from this donor shortName so the lecture offering still gets
# 20-seat lab sections.
SYNTHETIC_LAB_DONOR: Dict[str, str] = {
    "AI-Lab": "DAA-Lab",
}
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


def _offering_ext_id(subject_id: int) -> str:
    return f"taasika-io-{subject_id}"


def _course_ext_id(subject_id: int) -> str:
    # Must match courseCatalog.xml externalId for the controlling subject.
    return f"taasika-subject-{subject_id}"


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


def _teacher_for_division(lec_sections: List[dict], batch_name: str) -> int | None:
    """Pick the lecture teacher whose division matches a TY/SY batch name."""
    name = (batch_name or "").upper()
    if name.startswith("TY1") or name.startswith("SY1") or "DIV1" in name:
        want = 1
    elif name.startswith("TY2") or name.startswith("SY2") or "DIV2" in name:
        want = 2
    else:
        want = 1
    for entry in lec_sections:
        note = (entry.get("schedule_note") or "").upper()
        row = entry.get("row") or {}
        tid = row.get("teacherId")
        if not tid:
            continue
        if "DIV1" in note or note.endswith("1") or "CSE1" in note:
            if want == 1:
                return tid
        if "DIV2" in note or note.endswith("2") or "CSE2" in note:
            if want == 2:
                return tid
    if lec_sections:
        return (lec_sections[0].get("row") or {}).get("teacherId")
    return None


def _synthesize_lab_sections(
    lab_subj: dict,
    donor_subj: dict,
    sct_by_subject: Dict[int, List[dict]],
    sbt_by_subject: Dict[int, List[dict]],
    classes: dict,
    batches: dict,
    lec_sections: List[dict],
) -> List[dict]:
    """Clone donor lab batches onto a paired lab subject that has no mappings."""
    donor_sections = _build_lab_sections(
        donor_subj, sct_by_subject, sbt_by_subject, classes, batches
    )
    out: List[dict] = []
    for entry in donor_sections:
        row = dict(entry["row"])
        row["subjectId"] = lab_subj["subjectId"]
        teacher = _teacher_for_division(lec_sections, entry.get("schedule_note") or "")
        if teacher is not None:
            row["teacherId"] = teacher
        cloned = dict(entry)
        cloned["row"] = row
        cloned["limit"] = 20
        out.append(cloned)
    return out


def _apply_intake_limits(
    short: str,
    lec_sections: List[dict],
    lab_sections: List[dict],
) -> None:
    """Resize class limits to the confirmed intake; MDM/OE are room blocks only."""
    sn = short or ""
    notes = [entry.get("schedule_note") or "" for entry in lec_sections + lab_sections]
    year = year_from_notes(notes)

    if is_mdm_subject(sn):
        if lec_sections:
            for entry, lim in zip(lec_sections, even_split(len(lec_sections), MDM_BLOCK_SEATS)):
                entry["limit"] = lim
        lab_sections.clear()
        return

    if is_oe_subject(sn):
        if lec_sections:
            for entry, lim in zip(lec_sections, even_split(len(lec_sections), OE_BLOCK_SEATS)):
                entry["limit"] = lim
        return

    if year not in ("FY", "SY", "TY", "BT"):
        return

    demand = year_headcount(year)
    if is_de_subject(sn):
        n_opt = N_DE4_OPTIONS if sn.upper().startswith("DE4") else N_DE2_OPTIONS
        demand = (demand + n_opt - 1) // n_opt

    if lec_sections:
        limits = spread_demand(
            len(lec_sections), demand, [entry["limit"] for entry in lec_sections]
        )
        for entry, lim in zip(lec_sections, limits):
            entry["limit"] = lim
    if lab_sections:
        limits = spread_demand(
            len(lab_sections), demand, [entry["limit"] for entry in lab_sections]
        )
        for entry, lim in zip(lab_sections, limits):
            entry["limit"] = lim


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
    if EMIT_CLASS_ROOMS:
        for r in room_refs:
            lines.append(
                f'        <room id="taasika-room-{r["roomId"]}" '
                f'building="{_building_for(r["roomName"], r["roomShortName"])}" '
                f'roomNbr="{xml_escape(_room_number(r["roomShortName"]))}"/>'
            )
    if EMIT_CLASS_INSTRUCTORS and instructor_id is not None:
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
    incremental_attr = ' incremental="true"' if OFFERING_INCREMENTAL else ""
    lines.append(
        f'<offerings campus="{CAMPUS}" year="{YEAR}" term="{TERM}"{incremental_attr} '
        f'dateFormat="yyyy/M/d" timeFormat="HHmm" '
        f'created="Generated from Taasika snapshot 240" includeExams="none">'
    )

    offering_records: List[tuple[int, int | None]] = []
    section_offset: Dict[tuple[int, str], int] = {}
    skipped_no_mappings: List[str] = []
    skipped_honor: List[str] = []
    skipped_minor: List[str] = []
    used_offering_ids: List[int] = []
    class_limits: Dict[str, int] = {}
    class_notes: Dict[str, str] = {}
    subj_by_short = {s["subjectShortName"]: s for s in subjects}

    for primary in subjects:
        sid = primary["subjectId"]
        if sid in lab_to_lec:
            continue
        short = primary.get("subjectShortName") or ""
        if is_honor_subject(short):
            skipped_honor.append(f"{sid}:{short}")
            continue
        if is_minor_subject(short):
            skipped_minor.append(f"{sid}:{short}")
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
        if lab_subj and not lab_sections:
            donor_short = SYNTHETIC_LAB_DONOR.get(lab_subj.get("subjectShortName") or "")
            donor = subj_by_short.get(donor_short) if donor_short else None
            if donor:
                lab_sections = _synthesize_lab_sections(
                    lab_subj,
                    donor,
                    sct_by_subject,
                    sbt_by_subject,
                    classes,
                    batches,
                    lec_sections,
                )

        _apply_intake_limits(primary.get("subjectShortName") or "", lec_sections, lab_sections)

        if not lec_sections and not lab_sections:
            skipped_no_mappings.append(f"{sid}:{primary['subjectShortName']}")
            continue

        config_limit = sum(entry["limit"] for entry in lec_sections + lab_sections)
        if config_limit == 0:
            config_limit = 30

        area = info["subjectArea"]
        course_nbr = info["courseNumber"]
        title = info["title"]
        companion_kind = companion_itype((lab_subj or {}).get("subjectShortName") or "Lab")

        lec_min_per_week = 0
        if lec_subj and lec_sections:
            lec_min_per_week = (lec_subj.get("eachSlot") or 0) * (lec_subj.get("nSlots") or 0) * 60
            if is_mdm_subject(primary.get("subjectShortName") or ""):
                lec_min_per_week = MDM_LEC_MIN_PER_WEEK
            elif is_oe_subject(primary.get("subjectShortName") or ""):
                lec_min_per_week = OE_LEC_MIN_PER_WEEK
        lab_min_per_week = 0
        if lab_subj and lab_sections:
            lab_min_per_week = (lab_subj.get("eachSlot") or 0) * (lab_subj.get("nSlots") or 0) * 60

        used_offering_ids.append(sid)
        offering_ext = _offering_ext_id(sid)
        course_ext = _course_ext_id(sid)
        credits = info.get("credits")
        lines.append(f'  <offering id="{offering_ext}" offered="true" action="{OFFERING_ACTION}">')
        lines.append(
            f'    <course id="{course_ext}" subject="{xml_escape(area)}" '
            f'courseNbr="{xml_escape(course_nbr)}" controlling="true" '
            f'title="{xml_escape(title)}" '
            f'scheduleBookNote="{xml_escape(course_nbr)}">'
        )
        if credits is not None:
            lines.append(
                f'      <courseCredit creditType="collegiate" creditUnitType="semesterHours" '
                f'creditFormat="fixedUnit" fixedCredit="{credits}"/>'
            )
        lines.append("    </course>")
        lines.append(f'    <config name="1" limit="{config_limit}">')
        if lec_min_per_week > 0 and lec_sections:
            lines.append(f'      <subpart type="Lec" suffix="" minPerWeek="{lec_min_per_week}"/>')
        if lab_min_per_week > 0 and lab_sections:
            lines.append(
                f'      <subpart type="{companion_kind}" suffix="" minPerWeek="{lab_min_per_week}"/>'
            )

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
            class_limits[f"{area}|{course_nbr}|Lec|{idx}"] = int(entry["limit"] or 0)
            class_notes[f"{area}|{course_nbr}|Lec|{idx}"] = entry["schedule_note"] or ""

        for idx, entry in enumerate(lab_sections, start=1):
            row = entry["row"]
            cid = _class_id(area, course_nbr, companion_kind, idx)
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
                offset_key = (lab_subj["subjectId"], f"{companion_kind}-batch-{batch['batchId']}")
            else:
                cls = entry["class"]
                for cr in class_rooms_by_class.get(cls["classId"], [])[:1]:
                    room = rooms.get(cr["roomId"])
                    if room and (not room_refs or room["roomId"] != room_refs[0]["roomId"]):
                        room_refs.append(room)
                offset_key = (lab_subj["subjectId"], f"{companion_kind}-class-{cls['classId']}")
            _emit_class(
                lines,
                cid,
                companion_kind,
                idx,
                entry["limit"],
                entry["schedule_note"],
                room_refs,
                row.get("teacherId"),
            )
            section_offset[offset_key] = idx
            class_limits[f"{area}|{course_nbr}|{companion_kind}|{idx}"] = int(entry["limit"] or 0)
            class_notes[f"{area}|{course_nbr}|{companion_kind}|{idx}"] = entry["schedule_note"] or ""

        lines.append("    </config>")
        lines.append("  </offering>")
        offering_records.append((sid, lab_subj["subjectId"] if lab_subj else None))

    # Synthesize MDM Block offering
    mdm_block_id = 999000
    lines.append(
        f'  <offering externalId="taasika-offering-{mdm_block_id}" '
        f'offered="true" action="insert">'
    )
    lines.append(
        f'    <course subject="CS" courseNbr="MDM-BLOCK" '
        f'controlling="true"/>'
    )
    lines.append(f'    <config name="1" limit="{MDM_BLOCK_SEATS}">')
    lines.append(f'      <subpart type="Lec" minPerWeek="{MDM_LEC_MIN_PER_WEEK}">')
    lines.append(
        f'        <class externalId="taasika-class-{mdm_block_id}-Lec-1" '
        f'type="Lec" suffix="1" expectedCapacity="{MDM_BLOCK_SEATS}"/>'
    )
    lines.append('      </subpart>')
    lines.append('    </config>')
    lines.append('  </offering>')
    offering_records.append((mdm_block_id, None))
    class_limits["CS|MDM-BLOCK|Lec|1"] = MDM_BLOCK_SEATS

    lines.append("</offerings>\n")

    body = "\n".join(lines)
    out = OUT_DIR / "courseOffering.xml"
    out.write_text(body, encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} ({out.stat().st_size:,} bytes, "
        f"{len(used_offering_ids)} offerings)"
    )

    minimal_path = OUT_DIR / "courseOffering-minimal.xml"
    offering_start = offering_end = None
    for i, line in enumerate(lines):
        if line.startswith("  <offering "):
            if offering_start is None:
                offering_start = i
        elif offering_start is not None and line.startswith("  </offering>"):
            offering_end = i
            break
    if offering_start is not None and offering_end is not None:
        minimal_body = "\n".join(
            lines[:2] + lines[offering_start : offering_end + 1] + [lines[-1]]
        )
        minimal_path.write_text(minimal_body, encoding="utf-8")
        print(f"wrote {minimal_path.relative_to(OUT_DIR.parent)} (1 offering, for import debugging)")

    purge_lines = [
        "<!--",
        "  Optional purge. Do NOT import this while a timetable is saved/committed —",
        "  Hibernate throws TransientObjectException (CourseOffering still referenced).",
        "  Uncommit+delete the saved solution first, or skip purge and re-import with",
        "  action=update (python scripts/import_unitime.py).",
        "  Only taasika-io-* external ids are listed (numeric uniqueIds are not ours).",
        "-->",
        f'<offerings campus="{CAMPUS}" year="{YEAR}" term="{TERM}" incremental="true">',
    ]
    purge_sids: list[int] = []
    seen_purge: set[int] = set()
    for sid in list(used_offering_ids) + list(lab_to_lec) + [
        s["subjectId"] for s in subjects if skip_offering(s.get("subjectShortName") or "")
    ]:
        if sid in seen_purge:
            continue
        seen_purge.add(sid)
        purge_sids.append(sid)
    for sid in purge_sids:
        # Empty delete: a nested <course> with a mismatched id makes UniTime
        # instantiate a transient CourseOffering and fail the flush.
        purge_lines.append(
            f'  <offering id="{_offering_ext_id(sid)}" offered="false" action="delete"/>'
        )
    purge_lines.append("</offerings>\n")
    purge_path = OUT_DIR / "courseOffering-PURGE-all.xml"
    purge_path.write_text("\n".join(purge_lines), encoding="utf-8")
    print(f"wrote {purge_path.relative_to(OUT_DIR.parent)} ({len(purge_sids)} delete rows)")
    if skipped_honor:
        print(f"skipped {len(skipped_honor)} Honor offerings: {', '.join(skipped_honor)}")
    if skipped_minor:
        print(f"skipped {len(skipped_minor)} Minor offerings: {', '.join(skipped_minor)}")
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
        "skipped_honor": skipped_honor,
        "skipped_minor": skipped_minor,
        "class_limits": class_limits,
        "class_notes": class_notes,
    }
    (SCRIPTS_DIR / "offering_index.json").write_text(json.dumps(extra), encoding="utf-8")
    numbered = OUT_DIR / "12courseOffering.xml"
    numbered.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
