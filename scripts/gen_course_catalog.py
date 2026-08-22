"""Generate courseCatalog.xml and a reusable subject -> course index.

Lec subjects and their corresponding Lab/Tut subjects in Taasika are
collapsed into a single UniTime course (the Lec subject becomes the
controlling course; the Lab subject is absorbed as a subpart of the same
offering, see gen_course_offering.py).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from classifications import (
    clean_course_title,
    combined_credits,
    find_course_pairs,
    subject_area,
)


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent


def course_number_from_short(short_name: str, subject_id: int, used: set[str]) -> str:
    """Map Taasika shortName to a UniTime courseNbr shown on the timetable.

    UniTime displays ``subject + courseNbr`` (e.g. ``CS CN``). Keep the short
    code readable; replace characters that break XML/IDs.
    """
    raw = (short_name or "").strip() or f"X{subject_id}"
    # DS(FY) -> DS-FY ; PP(FY)-Lab already absorbed into primary PP(FY)
    cleaned = (
        raw.replace("(", "-")
        .replace(")", "")
        .replace(" ", "")
        .replace("/", "-")
        .replace("_", "-")
    )
    cleaned = re.sub(r"-+", "-", cleaned).strip("-") or f"X{subject_id}"
    # UniTime courseNbr length is limited in practice; keep a generous cap
    cleaned = cleaned[:32]
    base = cleaned
    n = 2
    while cleaned.upper() in used:
        suffix = f"-{n}"
        cleaned = (base[: 32 - len(suffix)] + suffix)
        n += 1
    used.add(cleaned.upper())
    return cleaned


def main() -> None:
    data = load(snapshot_id=240, tables=["subject"])
    subjects = sorted(data.filtered("subject"), key=lambda s: s["subjectId"])

    pairs = find_course_pairs(subjects)
    primary_of: dict[int, int] = pairs["primary_of"]
    lec_to_lab: dict[int, int] = pairs["lec_to_lab"]
    lab_to_lec: dict[int, int] = pairs["lab_to_lec"]
    subj_by_id = {s["subjectId"]: s for s in subjects}

    used_nbrs: set[str] = set()
    course_for_primary: dict[int, dict[str, object]] = {}
    rows: list[str] = []

    for s in subjects:
        sid = s["subjectId"]
        if sid in lab_to_lec:
            continue
        area = subject_area(s["subjectShortName"], s["subjectName"])
        course_nbr = course_number_from_short(s["subjectShortName"] or "", sid, used_nbrs)

        partner = subj_by_id.get(lec_to_lab.get(sid)) if sid in lec_to_lab else None
        is_paired = partner is not None
        is_lab_only = bool(s.get("batches")) and not is_paired

        if is_paired:
            credits = combined_credits(s, partner)
        elif is_lab_only:
            credits = combined_credits(None, s)
        else:
            credits = combined_credits(s, None)

        title = clean_course_title(s["subjectName"] or s["subjectShortName"] or "")
        permanent_id = f"taasika-{sid}"
        external_id = f"taasika-subject-{sid}"

        rows.append(
            f'  <course externalId="{external_id}" subject="{area}" '
            f'courseNumber="{xml_escape(course_nbr)}" title="{xml_escape(title)}" '
            f'permanentId="{permanent_id}">'
        )
        rows.append(
            f'    <courseCredit creditType="collegiate" creditUnitType="semesterHours" '
            f'creditFormat="fixedUnit" fixedCredit="{credits}"/>'
        )
        rows.append("  </course>")

        course_for_primary[sid] = {
            "subjectArea": area,
            "courseNumber": course_nbr,
            "title": title,
            "credits": credits,
            "lecSubjectId": sid if not is_lab_only else None,
            "labSubjectId": partner["subjectId"] if partner else (sid if is_lab_only else None),
        }

    index: dict[str, dict[str, object]] = {}
    for sid in subj_by_id:
        primary = primary_of.get(sid, sid)
        course = course_for_primary.get(primary)
        if not course:
            continue
        s = subj_by_id[sid]
        index[str(sid)] = {
            "subjectArea": course["subjectArea"],
            "courseNumber": course["courseNumber"],
            "title": course["title"],
            "shortName": s["subjectShortName"],
            # A subject is a "lab" only if it's the paired companion
            # (sid in lab_to_lec) or a genuinely unpaired batch-registered
            # subject (no lecture partner found). Raw ``batches`` alone is
            # not sufficient: batch-registered elective lectures (DE/Honor/
            # PSEC/MDM) also have batches=1 but are the Lec side of a pair.
            "isLab": sid in lab_to_lec or (bool(s.get("batches")) and sid not in lec_to_lab),
            "eachSlot": s.get("eachSlot") or 0,
            "nSlots": s.get("nSlots") or 0,
            "credits": course["credits"],
            "primarySubjectId": primary,
        }

    out_lines: list[str] = [LICENSE_HEADER]
    out_lines.append(f'<courseCatalog campus="{CAMPUS}" term="{TERM}" year="{YEAR}">')
    out_lines.extend(rows)
    out_lines.append("</courseCatalog>\n")

    catalog_path = OUT_DIR / "courseCatalog.xml"
    catalog_path.write_text("\n".join(out_lines), encoding="utf-8")

    index_path = SCRIPTS_DIR / "subject_index.json"
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    paired = sum(1 for sid in subj_by_id if sid in lec_to_lab)
    print(
        f"wrote {catalog_path.relative_to(OUT_DIR.parent)} "
        f"({catalog_path.stat().st_size:,} bytes, {len(course_for_primary)} courses; "
        f"{paired} merged Lec+Lab/Tut pairs absorbed)"
    )
    print(f"wrote {index_path.relative_to(OUT_DIR.parent)} (subject -> course index, {len(index)} entries)")


if __name__ == "__main__":
    main()
