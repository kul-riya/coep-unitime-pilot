"""Standalone student-conflict checker for a CPSolver timetable XML. No JVM, stdlib only.

Same overlap rule as the Java ConflictOracle: two of a student's assigned classes conflict if
they share a weekday and their times overlap. Date-pattern/week overlap is skipped — ponytail:
this dataset is 100% "Full Term", so week overlap is always true; add BitSet intersection via the
<dates>/<date pattern=...> table if a half-term course ever shows up.

    python -m unitime_rl.check_conflicts FILE.xml [--labels timetable_or_offerings.xml] [-n 15]
"""
from __future__ import annotations

import argparse
import sys
from xml.etree import ElementTree as ET

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # index i <-> days-string char i


def load_classes(root: ET.Element) -> dict[str, dict]:
    classes = {}
    for c in root.find("classes").findall("class"):
        t = next((te for te in c.findall("time") if te.get("solution") == "true"), None)
        if t is None:
            continue  # unassigned class, cannot conflict
        classes[c.get("id")] = {"days": t.get("days"), "start": int(t.get("start")), "length": int(t.get("length"))}
    return classes


def overlaps(a: dict, b: dict) -> bool:
    if not any(x == "1" and y == "1" for x, y in zip(a["days"], b["days"])):
        return False
    return a["start"] < b["start"] + b["length"] and b["start"] < a["start"] + a["length"]


def check(root: ET.Element) -> tuple[float, int, int, int, list[tuple[str, str, str]]]:
    classes = load_classes(root)
    students = root.find("students")
    if students is None or len(students) == 0:
        sys.exit("no <student> elements in this file — inject enrollments first (unitime_rl.inject_students)")
    conflicted = two_plus = 0
    examples: list[tuple[str, str, str]] = []
    for st in students.findall("student"):
        ids = [c.get("id") for c in st.findall("class") if c.get("id") in classes]
        if len(ids) < 2:
            continue
        two_plus += 1
        hit = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if overlaps(classes[ids[i]], classes[ids[j]]):
                    hit = True
                    examples.append((st.get("id"), ids[i], ids[j]))
        conflicted += hit
    c = conflicted / two_plus if two_plus else 0.0
    return c, conflicted, two_plus, len(students), examples


def slot_to_hhmm(slot: int) -> str:
    m = slot * 5
    return f"{m // 60:02d}:{m % 60:02d}"


def fmt_class(cls: dict) -> str:
    days = "".join(n for n, b in zip(DAY_NAMES, cls["days"]) if b == "1")
    return f"{days} {slot_to_hhmm(cls['start'])}-{slot_to_hhmm(cls['start'] + cls['length'])}"


def load_labels(path: str) -> dict[str, str]:
    labels = {}
    for c in ET.parse(path).getroot().iter("class"):
        cid = c.get("id")
        if not cid:
            continue
        labels[cid] = c.get("scheduleNote") or f"{c.get('subject', '')} {c.get('courseNbr', '')} {c.get('type', '')}{c.get('suffix', '')}".strip()
    return labels


def _selftest() -> None:
    a = {"days": "1000000", "start": 100, "length": 12}   # Mon 08:20-09:20
    b = {"days": "1000000", "start": 106, "length": 12}   # Mon 08:50-09:50 -> overlaps a
    c = {"days": "1000000", "start": 112, "length": 12}   # Mon 09:20-10:20 -> touches a, no overlap
    d = {"days": "0100000", "start": 100, "length": 12}   # Tue, same time, different day
    assert overlaps(a, b) is True
    assert overlaps(a, c) is False
    assert overlaps(a, d) is False
    print("selftest ok")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xml", nargs="?", help="CPSolver timetable XML (must have <student> enrollments)")
    ap.add_argument("--labels", help="a timetable/offerings XML sharing the same class ids, for readable names")
    ap.add_argument("-n", "--examples", type=int, default=15)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest or not args.xml:
        _selftest()
        if not args.xml:
            return

    root = ET.parse(args.xml).getroot()
    c, conflicted, two_plus, total, examples = check(root)
    print(f"C = {c:.4f}  ({conflicted}/{two_plus} students with >=2 classes conflicted; {total} students total)")

    labels = load_labels(args.labels) if args.labels else {}
    classes = load_classes(root)
    print(f"\nexample conflicts (showing up to {args.examples} of {len(examples)}):")
    for sid, c1, c2 in examples[: args.examples]:
        print(f"  student {sid}: {labels.get(c1, c1)} [{fmt_class(classes[c1])}]  overlaps  {labels.get(c2, c2)} [{fmt_class(classes[c2])}]")


if __name__ == "__main__":
    main()
