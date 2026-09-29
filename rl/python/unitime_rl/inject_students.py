"""Add student enrollments to a CPSolver timetable XML whose <students/> is empty.

The UniTime solver only sees students through its "Student Course Demands" class. When that is
"Projected Student Course Demands" and the session has no curricula or last-like demands, the
export carries no students. The Data Exchange studentEnrollments export (StudentClassEnrollment)
references classes by their UniTime unique ids, which are the class ids of the solver XML, so the
same data that "Enrolled Student Course Demands" would load can be written straight into the file:

    <students>
      <student id="610103001">
        <offering id="5341240"/>       one per distinct offering of the student's classes
        <class id="4588043"/>          one per enrolled class
      </student>
    </students>

    python -m unitime_rl.inject_students --solver-xml instances/spr2026-nostudents.xml \
        --enrollments ../unitime-out-spr6/studentEnrollments.xml --out instances/spr2026.xml
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


def inject(solver_xml: Path, enrollments_xml: Path, out: Path, weight: float = 1.0) -> dict:
    tree = ET.parse(solver_xml)
    root = tree.getroot()
    if root.tag != "timetable" or root.find("classes") is None:
        raise SystemExit(f"{solver_xml} is not a CPSolver timetable XML (root <timetable> with <classes>)")
    classes = {c.get("id"): c for c in root.find("classes").findall("class")}
    students_el = root.find("students")
    if students_el is None:
        students_el = ET.SubElement(root, "students")
    existing = len(students_el.findall("student"))
    if existing:
        raise SystemExit(f"{solver_xml} already has {existing} students; refusing to overwrite")

    enr = ET.parse(enrollments_xml).getroot()
    if enr.tag != "studentEnrollments":
        raise SystemExit(f"{enrollments_xml} is not a Data Exchange studentEnrollments file")
    stats = Counter()
    per_student: dict[str, list[str]] = defaultdict(list)
    for st in enr.findall("student"):
        sid = st.get("externalId") or st.get("id")
        if sid is None:
            stats["student_without_id"] += 1
            continue
        try:
            int(sid)
        except ValueError:
            stats["student_non_numeric_id"] += 1
            continue
        for c in st.findall("class"):
            cid = c.get("id")
            if cid is None or cid not in classes:
                stats["enrollment_unknown_class"] += 1
                continue
            per_student[sid].append(cid)
            stats["enrollments"] += 1

    for sid in sorted(per_student, key=int):
        cids = sorted(set(per_student[sid]), key=int)
        st_el = ET.SubElement(students_el, "student", {"id": sid})
        offerings = []
        for cid in cids:
            off = classes[cid].get("offering")
            if off and off not in offerings:
                offerings.append(off)
        for off in offerings:
            attrs = {"id": off}
            if weight != 1.0:
                attrs["weight"] = f"{weight:g}"
            ET.SubElement(st_el, "offering", attrs)
        for cid in cids:
            ET.SubElement(st_el, "class", {"id": cid})
        stats["students"] += 1
        stats["students_two_plus"] += 1 if len(cids) >= 2 else 0
    ET.indent(tree, space="  ")
    out.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    return dict(stats)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solver-xml", required=True)
    ap.add_argument("--enrollments", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--weight", type=float, default=1.0, help="offering weight per student (UniTime default 1.0)")
    args = ap.parse_args(argv)
    stats = inject(Path(args.solver_xml), Path(args.enrollments), Path(args.out), args.weight)
    print(f"wrote {args.out}: {stats}")


if __name__ == "__main__":
    main()
