"""Generate mock studentInfo.xml, studentRequest.xml, and studentenrollments.xml.

Taasika does not track individual students, so we synthesise a roster of
``class.classCount`` students per class.  Each mock student is:

* given an externalId of the form ``<classShortName>-S<index>``;
* mapped to a UniTime ``academicArea`` / ``academicClassification`` / ``posMajor``
  consistent with the Major.xml / academicClassification.xml output;
* added to the ``studentGroup`` of their parent class and (round-robin) of one
  batch that belongs to that class;
* enrolled in the Lec section of every subject taught to their class
  (subjectClassTeacher) and in the corresponding Lab section of every Lab
  subject taught to their batch (subjectBatchTeacher).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from classifications import major_for_class, year_classification
from gen_academic import area_for_class


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent

GIVEN_NAMES = [
    "Aarav", "Aanya", "Aditya", "Ananya", "Arjun", "Bhavika", "Chirag", "Diya",
    "Dev", "Esha", "Farhan", "Gauri", "Harsh", "Ishita", "Jai", "Kavya",
    "Lakshay", "Meera", "Neel", "Omkar", "Priya", "Rahul", "Riya", "Sahil",
    "Tara", "Uday", "Varun", "Yash", "Zara", "Aditi",
]

LAST_NAMES = [
    "Patil", "Sharma", "Kulkarni", "Joshi", "Deshpande", "Iyer", "Nair",
    "Verma", "Gupta", "Singh", "Rao", "Reddy", "Khan", "Mehta", "Shah",
]


def _student_external_id(class_short: str, idx: int) -> str:
    return f"{class_short}-S{idx:03d}"


def _student_name(idx: int) -> tuple[str, str]:
    first = GIVEN_NAMES[idx % len(GIVEN_NAMES)]
    last = LAST_NAMES[(idx // len(GIVEN_NAMES)) % len(LAST_NAMES)]
    return first, last


def main() -> None:
    data = load(
        snapshot_id=240,
        tables=[
            "class",
            "batch",
            "batchClass",
            "subject",
            "subjectClassTeacher",
            "subjectBatchTeacher",
        ],
    )
    classes = sorted(data.filtered("class"), key=lambda c: c["classId"])
    classes_by_id: Dict[int, dict] = {c["classId"]: c for c in classes}
    subjects = {s["subjectId"]: s for s in data.filtered("subject")}

    batches_by_class: Dict[int, List[int]] = defaultdict(list)
    for row in data.filtered("batchClass"):
        batches_by_class[row["classId"]].append(row["batchId"])

    sct_by_class: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("subjectClassTeacher"):
        sct_by_class[row["classId"]].append(row)

    sbt_by_batch: Dict[int, List[dict]] = defaultdict(list)
    for row in data.filtered("subjectBatchTeacher"):
        sbt_by_batch[row["batchId"]].append(row)

    offering_index = json.loads(
        (SCRIPTS_DIR / "offering_index.json").read_text(encoding="utf-8")
    )
    offered: set[int] = set(offering_index["offerings"])
    subject_idx: Dict[str, dict] = json.loads(
        (SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8")
    )
    batch_name_by_id: Dict[int, str] = {b["batchId"]: b["batchName"] for b in data.filtered("batch")}

    raw_offsets = offering_index.get("section_offsets", {})
    section_offset_map: Dict[tuple[int, str], int] = {}
    for key, val in raw_offsets.items():
        sid_str, rest = key.split("|", 1)
        section_offset_map[(int(sid_str), rest)] = val

    def offered_for(subject_id: int) -> bool:
        info = subject_idx.get(str(subject_id))
        if not info:
            return False
        return info.get("primarySubjectId") in offered

    info_lines: List[str] = [LICENSE_HEADER]
    info_lines.append(f'<students campus="{CAMPUS}" year="{YEAR}" term="{TERM}">')

    req_lines: List[str] = [LICENSE_HEADER]
    req_lines.append(f'<request campus="{CAMPUS}" year="{YEAR}" term="{TERM}">')

    enr_lines: List[str] = [LICENSE_HEADER]
    enr_lines.append(f'<studentEnrollments campus="{CAMPUS}" year="{YEAR}" term="{TERM}">')

    section_offset = section_offset_map

    total_students = 0
    for cls in classes:
        class_id = cls["classId"]
        short = cls["classShortName"]
        count = cls["classCount"] or 0
        if count <= 0:
            continue
        total_students += count

        area = area_for_class(short)
        class_code, _ = year_classification(short, cls["semester"])
        major_code, _ = major_for_class(short, cls["className"])

        class_batches = batches_by_class.get(class_id, [])

        for i in range(count):
            ext_id = _student_external_id(short, i + 1)
            first, last = _student_name(i)
            email = f"{ext_id.lower()}@students.unitime.local"

            info_lines.append(
                f'  <student externalId="{xml_escape(ext_id)}" '
                f'firstName="{xml_escape(first)}" lastName="{xml_escape(last)}" '
                f'email="{xml_escape(email)}">'
            )
            info_lines.append('    <studentAcadAreaClass>')
            info_lines.append(
                f'      <acadAreaClass academicArea="{area}" academicClass="{class_code}"/>'
            )
            info_lines.append('    </studentAcadAreaClass>')
            info_lines.append('    <studentMajors>')
            info_lines.append(
                f'      <major academicArea="{area}" academicClass="{class_code}" code="{major_code}"/>'
            )
            info_lines.append('    </studentMajors>')
            info_lines.append('    <studentGroups>')
            info_lines.append(f'      <studentGroup group="{xml_escape(short)}"/>')
            if class_batches:
                batch_id = class_batches[i % len(class_batches)]
                batch_name = batch_name_by_id.get(batch_id)
                if batch_name:
                    info_lines.append(
                        f'      <studentGroup group="{xml_escape(batch_name)}"/>'
                    )
            info_lines.append('    </studentGroups>')
            info_lines.append('  </student>')

            req_lines.append(f'  <student key="{xml_escape(ext_id)}">')
            req_lines.append('    <updateCourseRequests commit="true">')
            student_courses: List[tuple[str, str]] = []
            for sct in sct_by_class.get(class_id, []):
                if not offered_for(sct["subjectId"]):
                    continue
                info = subject_idx.get(str(sct["subjectId"]))
                if not info:
                    continue
                student_courses.append((info["subjectArea"], info["courseNumber"]))
            if class_batches:
                batch_id = class_batches[i % len(class_batches)]
                for sbt in sbt_by_batch.get(batch_id, []):
                    if not offered_for(sbt["subjectId"]):
                        continue
                    info = subject_idx.get(str(sbt["subjectId"]))
                    if not info:
                        continue
                    student_courses.append((info["subjectArea"], info["courseNumber"]))
            seen: set[tuple[str, str]] = set()
            for area_abbr, course_nbr in student_courses:
                if (area_abbr, course_nbr) in seen:
                    continue
                seen.add((area_abbr, course_nbr))
                req_lines.append(
                    f'      <courseOffering subjectArea="{xml_escape(area_abbr)}" courseNumber="{xml_escape(course_nbr)}"/>'
                )
            req_lines.append('    </updateCourseRequests>')
            req_lines.append('  </student>')

            enr_lines.append(f'  <student externalId="{xml_escape(ext_id)}">')
            for sct in sct_by_class.get(class_id, []):
                if not offered_for(sct["subjectId"]):
                    continue
                suffix = section_offset.get(
                    (sct["subjectId"], f"Lec-class-{class_id}")
                )
                if suffix is None:
                    continue
                info = subject_idx.get(str(sct["subjectId"]))
                if not info:
                    continue
                enr_lines.append(
                    f'    <class subject="{xml_escape(info["subjectArea"])}" '
                    f'courseNbr="{xml_escape(info["courseNumber"])}" '
                    f'type="Lec" suffix="{suffix}"/>'
                )
            if class_batches:
                batch_id = class_batches[i % len(class_batches)]
                for sbt in sbt_by_batch.get(batch_id, []):
                    if not offered_for(sbt["subjectId"]):
                        continue
                    suffix = section_offset.get(
                        (sbt["subjectId"], f"Lab-batch-{batch_id}")
                    )
                    if suffix is None:
                        continue
                    info = subject_idx.get(str(sbt["subjectId"]))
                    if not info:
                        continue
                    enr_lines.append(
                        f'    <class subject="{xml_escape(info["subjectArea"])}" '
                        f'courseNbr="{xml_escape(info["courseNumber"])}" '
                        f'type="Lab" suffix="{suffix}"/>'
                    )
            enr_lines.append('  </student>')

    info_lines.append('</students>\n')
    req_lines.append('</request>\n')
    enr_lines.append('</studentEnrollments>\n')

    (OUT_DIR / "studentInfo.xml").write_text("\n".join(info_lines), encoding="utf-8")
    (OUT_DIR / "studentRequest.xml").write_text("\n".join(req_lines), encoding="utf-8")
    (OUT_DIR / "studentenrollments.xml").write_text("\n".join(enr_lines), encoding="utf-8")

    for name in ("studentInfo.xml", "studentRequest.xml", "studentenrollments.xml"):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")
    print(f"total mock students generated: {total_students}")


if __name__ == "__main__":
    main()
