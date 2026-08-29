"""Verify Taasika subject durations match preferences.xml time patterns.

Compares snapshot 240 ``eachSlot * nSlots * 60`` for every schedulable offering
subpart against the required ``timePref`` in ``unitime-out/preferences.xml``.

Usage:
  python scripts/verify_time_patterns.py
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from classifications import companion_itype, find_course_pairs, skip_offering
from gen_course_offering import (
    SYNTHETIC_LAB_DONOR,
    _build_lab_sections,
    _build_lec_sections,
    _synthesize_lab_sections,
)
from gen_preferences import _time_pattern
from intake import (
    MDM_LEC_MIN_PER_WEEK,
    OE_LEC_MIN_PER_WEEK,
    is_mdm_subject,
    is_oe_subject,
)
from taasika_loader import load

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent


def expected_patterns(snapshot_id: int = 240) -> dict[tuple[str, str, str], str]:
    """(subject, courseNbr, type) -> pattern name from Taasika + subject_index."""
    data = load(
        snapshot_id=snapshot_id,
        tables=["subject", "class", "batch", "subjectClassTeacher", "subjectBatchTeacher"],
    )
    subjects = list(data.filtered("subject"))
    subj_by_id = {s["subjectId"]: s for s in subjects}
    classes = {c["classId"]: c for c in data.filtered("class")}
    batches = {b["batchId"]: b for b in data.filtered("batch")}
    sct_by_subject: dict[int, list] = {}
    for row in data.filtered("subjectClassTeacher"):
        sct_by_subject.setdefault(row["subjectId"], []).append(row)
    sbt_by_subject: dict[int, list] = {}
    for row in data.filtered("subjectBatchTeacher"):
        sbt_by_subject.setdefault(row["subjectId"], []).append(row)
    idx = json.loads((SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8"))
    pairs = find_course_pairs(subjects)
    lab_to_lec = pairs["lab_to_lec"]
    lec_to_lab = pairs["lec_to_lab"]

    out: dict[tuple[str, str, str], str] = {}
    for primary in subjects:
        sid = primary["subjectId"]
        if sid in lab_to_lec:
            continue
        short = primary.get("subjectShortName") or ""
        if skip_offering(short):
            continue
        info = idx.get(str(sid))
        if not info:
            continue

        # Mirror gen_course_offering.py: batches=1 alone does not mean "lab
        # only" -- batch-registered elective lectures (DE/Honor/PSEC/MDM)
        # can have batches=1 too. Only treat as lab-only when unpaired.
        is_lab_only = bool(primary.get("batches")) and sid not in lec_to_lab
        lec_subj = None if is_lab_only else primary
        lab_subj = None
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
            donor = subj_by_id.get(
                next(
                    (s["subjectId"] for s in subjects if s.get("subjectShortName") == donor_short),
                    0,
                )
            ) if donor_short else None
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
        if not lec_sections and not lab_sections:
            continue

        area = info["subjectArea"]
        course_nbr = info["courseNumber"]
        if lec_subj and lec_sections:
            mins = (lec_subj.get("eachSlot") or 0) * (lec_subj.get("nSlots") or 0) * 60
            if is_mdm_subject(short):
                mins = MDM_LEC_MIN_PER_WEEK
            elif is_oe_subject(short):
                mins = OE_LEC_MIN_PER_WEEK
            if mins > 0:
                out[(area, course_nbr, "Lec")] = _time_pattern("Lec", mins)
        if lab_subj and lab_sections and not is_mdm_subject(short):
            mins = (lab_subj.get("eachSlot") or 0) * (lab_subj.get("nSlots") or 0) * 60
            if mins > 0:
                kind = companion_itype(lab_subj.get("subjectShortName") or "Lab")
                out[(area, course_nbr, kind)] = _time_pattern(kind, mins)
    return out


def actual_patterns(path: Path) -> dict[tuple[str, str, str], str]:
    root = ET.parse(path).getroot()
    out: dict[tuple[str, str, str], str] = {}
    for sp in root.findall("subpart"):
        tp = sp.find("timePref")
        if tp is None:
            continue
        key = (sp.get("subject", ""), sp.get("course", ""), sp.get("type", ""))
        out[key] = tp.get("pattern", "")
    return out


def main() -> int:
    prefs_path = OUT_DIR / "13preferences.xml" if (OUT_DIR / "13preferences.xml").is_file() else OUT_DIR / "preferences.xml"
    if not prefs_path.is_file():
        print(f"ERROR: {prefs_path} not found", file=sys.stderr)
        return 1

    expected = expected_patterns()
    actual = actual_patterns(prefs_path)

    missing_in_prefs: list[str] = []
    mismatches: list[str] = []
    for key, exp in sorted(expected.items()):
        subj, course, typ = key
        label = f"{subj} {course} {typ}"
        got = actual.get(key)
        if got is None:
            missing_in_prefs.append(label)
        elif got != exp:
            mismatches.append(f"{label}: expected {exp!r}, got {got!r}")

    extra = [f"{k[0]} {k[1]} {k[2]}={v}" for k, v in sorted(actual.items()) if k not in expected]

    print("Time pattern audit (Taasika snapshot 240 -> preferences.xml)")
    print(f"  expected subparts : {len(expected)}")
    print(f"  prefs subparts    : {len(actual)}")
    print(f"  pattern counts    : {dict(Counter(actual.values()))}")

    fy = expected.get(("CS", "FY-Reserve", "Lec"))
    if fy:
        print(f"  FY-Reserve Lec    : {fy} (eachSlot=1, nSlots=5 -> 300 min/wk)")

    ok = not missing_in_prefs and not mismatches
    if missing_in_prefs:
        print(f"\nMISSING in preferences.xml ({len(missing_in_prefs)}):")
        for line in missing_in_prefs[:20]:
            print(f"  - {line}")
        if len(missing_in_prefs) > 20:
            print(f"  ... and {len(missing_in_prefs) - 20} more")
    if mismatches:
        print(f"\nMISMATCH ({len(mismatches)}):")
        for line in mismatches[:20]:
            print(f"  - {line}")
    if extra:
        print(f"\nEXTRA in preferences.xml (not in offerings): {len(extra)}")
        for line in extra[:8]:
            print(f"  - {line}")

    if ok:
        print("\nOK: all offering subparts match Taasika -> preferences.xml")
        return 0
    print("\nFAIL: regenerate preferences with  python scripts/gen_preferences.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
