"""Generate preferences.xml with time/date patterns and fixed-cohort constraints.

UniTime's course timetabling solver requires each class to have a time pattern
before it can be loaded.  ``courseOffering.xml`` defines minutes/week on
subparts but not patterns; this file fills that gap via the Preferences XML
import (Administration > Academic Sessions > Data Exchange).

Reference: https://www.unitime.org/interface/preferences.xml
"""

from __future__ import annotations

import collections
import itertools
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
    if min_per_week == 240:
        return "2 x 120" if subpart_type == "Lab" else "4 x 60"
    if min_per_week == 300:
        return "5 x 60"
    raise ValueError(
        f"no time pattern for {subpart_type} with minPerWeek={min_per_week}"
    )


def main() -> None:
    src = OUT_DIR / "courseOffering.xml"
    root = ET.parse(src).getroot()

    # A required SAME_STUDENTS preference is emitted for every group of lecture
    # sections with an identical enrolled-student cohort.  This is data-driven:
    # it keeps all courses taken by a division aligned without assuming that a
    # human-readable section suffix means the same thing in every offering.
    enrollments = ET.parse(OUT_DIR / "studentenrollments.xml").getroot()
    students_by_lecture: dict[tuple[str, str, str], set[str]] = collections.defaultdict(set)
    for student in enrollments.findall("student"):
        external_id = student.get("externalId")
        if not external_id:
            continue
        for cls in student.findall("class"):
            if cls.get("type") != "Lec":
                continue
            key = (cls.get("subject", ""), cls.get("courseNbr", ""), cls.get("suffix", ""))
            students_by_lecture[key].add(external_id)

    cohort_groups: dict[frozenset[str], list[tuple[str, str, str]]] = collections.defaultdict(list)
    for key, students in students_by_lecture.items():
        if students:
            cohort_groups[frozenset(students)].append(key)
    same_student_peers: dict[tuple[str, str, str], list[tuple[str, str, str]]] = {}
    for sections in cohort_groups.values():
        if len(sections) < 2:
            continue
        sections.sort()
        same_student_peers[sections[0]] = sections[1:]

    # The enrollment file also represents a fixed section roster for this
    # pilot.  A partial cohort intersection must be protected too: for
    # example, a 50-student elective section can share students with a
    # 250-student core section without having an identical cohort.  UniTime's
    # demand-based student-conflict metric may re-section such students into
    # alternatives, so emit a hard DIFFERENT_TIME preference for every such
    # fixed-section pair.  Pairs already covered by SAME_STUDENTS are omitted
    # to avoid writing redundant hard constraints.
    offered_classes: set[tuple[str, str, str, str]] = set()
    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue
        subject = course.get("subject", "")
        course_nbr = course.get("courseNbr", "")
        for cls in offering.iter("class"):
            if cls.get("cancelled", "false").lower() != "true":
                offered_classes.add(
                    (subject, course_nbr, cls.get("type", ""), cls.get("suffix", ""))
                )

    same_student_pairs: set[
        tuple[tuple[str, str, str, str], tuple[str, str, str, str]]
    ] = set()
    for sections in cohort_groups.values():
        lecture_classes = sorted(
            (subject, course_nbr, "Lec", suffix)
            for subject, course_nbr, suffix in sections
            if (subject, course_nbr, "Lec", suffix) in offered_classes
        )
        same_student_pairs.update(itertools.combinations(lecture_classes, 2))

    fixed_section_pairs: set[
        tuple[tuple[str, str, str, str], tuple[str, str, str, str]]
    ] = set()
    for student in enrollments.findall("student"):
        classes = sorted(
            {
                (cls.get("subject", ""), cls.get("courseNbr", ""), cls.get("type", ""), cls.get("suffix", ""))
                for cls in student.findall("class")
                if (cls.get("subject", ""), cls.get("courseNbr", ""), cls.get("type", ""), cls.get("suffix", ""))
                in offered_classes
            }
        )
        fixed_section_pairs.update(itertools.combinations(classes, 2))
    fixed_section_pairs.difference_update(same_student_pairs)

    different_time_peers: dict[
        tuple[str, str, str, str], list[tuple[str, str, str, str]]
    ] = collections.defaultdict(list)
    for first, second in sorted(fixed_section_pairs):
        different_time_peers[first].append(second)

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
            # ``iter`` is essential here: Lab subparts and their classes are
            # nested under their parent Lec after the parent-child fix.
            subparts = {
                sp.get("type", ""): sp
                for sp in config.iter("subpart")
            }
            classes_by_type: dict[str, list[ET.Element]] = {}
            for cls in config.iter("class"):
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
                    lecture_key = (subject, course_nbr, cls_suffix)
                    peers = same_student_peers.get(lecture_key, []) if sp_type == "Lec" else []
                    fixed_peers = different_time_peers.get(
                        (subject, course_nbr, sp_type, cls_suffix), []
                    )
                    lines.append(
                        f'  <class subject="{xml_escape(subject)}" '
                        f'course="{xml_escape(course_nbr)}" '
                        f'type="{xml_escape(sp_type)}" '
                        f'suffix="{xml_escape(cls_suffix)}"'
                    )
                    if not peers and not fixed_peers:
                        lines[-1] += "/>"
                    else:
                        lines[-1] += ">"
                        if peers:
                            lines.append('    <distributionPref type="SAME_STUDENTS" level="R">')
                            for peer_subject, peer_course, peer_suffix in peers:
                                lines.append(
                                    f'      <class subject="{xml_escape(peer_subject)}" '
                                    f'course="{xml_escape(peer_course)}" type="Lec" '
                                    f'suffix="{xml_escape(peer_suffix)}"/>'
                                )
                            lines.append("    </distributionPref>")
                        if fixed_peers:
                            for peer_subject, peer_course, peer_type, peer_suffix in fixed_peers:
                                # A distribution preference with more than two
                                # classes is an all-classes constraint.  Emit
                                # one two-class preference per roster pair so
                                # non-overlapping peers are not accidentally
                                # made mutually exclusive.
                                # UniTime's Preferences XML uses the database
                                # distribution reference (DIFF_TIME), not the
                                # display label "Different Time".
                                lines.append('    <distributionPref type="DIFF_TIME" level="R">')
                                lines.append(
                                    f'      <class subject="{xml_escape(peer_subject)}" '
                                    f'course="{xml_escape(peer_course)}" '
                                    f'type="{xml_escape(peer_type)}" '
                                    f'suffix="{xml_escape(peer_suffix)}"/>'
                                )
                                lines.append("    </distributionPref>")
                        lines.append("  </class>")

    lines.append("</preferences>\n")

    out = OUT_DIR / "preferences.xml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {out.relative_to(OUT_DIR.parent)} "
        f"({out.stat().st_size:,} bytes, {subpart_count} subparts, {class_count} classes, "
        f"{len(same_student_peers)} SAME_STUDENTS groups, "
        f"{len(fixed_section_pairs)} DIFF_TIME pairs)"
    )


if __name__ == "__main__":
    main()
