"""Print a human-readable summary of a Taasika snapshot."""

from __future__ import annotations

import json
import sys
from collections import Counter

from taasika_loader import load


def main() -> None:
    snap = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    data = load(snapshot_id=snap)

    print("=== Departments (snapshot-independent) ===")
    for d in data.rows("dept"):
        print(f"  deptId={d['deptId']}  short={d['deptShortName']:<8} name={d['deptName']}")

    print("\n=== Config (snapshot-independent) ===")
    for c in data.rows("config"):
        print(f"  {c}")

    print(f"\n=== Snapshot row(s) for id={snap} (informational) ===")
    for s in data.rows("snapshot"):
        if s["snapshotId"] == snap:
            print(f"  {s}")

    classes = data.filtered("class")
    print(f"\n=== Classes ({len(classes)}) ===")
    for c in classes:
        print(
            f"  classId={c['classId']:<5} short={c['classShortName']:<12} "
            f"sem={c['semester']:<2} count={c['classCount']:<3} name={c['className']}"
        )

    batches = data.filtered("batch")
    print(f"\n=== Batches ({len(batches)}) ===")
    for b in batches[:30]:
        print(f"  batchId={b['batchId']:<5} name={b['batchName']:<14} count={b['batchCount']}")
    if len(batches) > 30:
        print(f"  ... +{len(batches) - 30} more")

    rooms = data.filtered("room")
    print(f"\n=== Rooms ({len(rooms)}) ===")
    for r in rooms:
        print(
            f"  roomId={r['roomId']:<5} short={r['roomShortName']:<14} cap={r['roomCount']:<4} name={r['roomName']}"
        )

    teachers = data.filtered("teacher")
    print(f"\n=== Teachers ({len(teachers)}) ===")
    dept_count = Counter(t["deptId"] for t in teachers)
    print(f"  by deptId: {dict(dept_count)}")
    hours = Counter((t["minHrs"], t["maxHrs"]) for t in teachers)
    print(f"  (minHrs,maxHrs) distribution: {dict(hours)}")
    for t in teachers[:15]:
        print(
            f"  teacherId={t['teacherId']:<5} short={t['teacherShortName']:<14} "
            f"min={t['minHrs']:<3} max={t['maxHrs']:<3} dept={t['deptId']}"
        )
    if len(teachers) > 15:
        print(f"  ... +{len(teachers) - 15} more")

    subjects = data.filtered("subject")
    print(f"\n=== Subjects ({len(subjects)}) ===")
    by_batches = Counter(s["batches"] for s in subjects)
    print(f"  batches flag distribution: {dict(by_batches)}")
    slot_dist = Counter((s["eachSlot"], s["nSlots"], s["batches"]) for s in subjects)
    print(f"  (eachSlot,nSlots,batches) distribution: {dict(slot_dist)}")
    for s in subjects[:25]:
        print(
            f"  subjectId={s['subjectId']:<6} short={s['subjectShortName']:<16} "
            f"each={s['eachSlot']:<2} n={s['nSlots']:<2} batches={s['batches']} name={s['subjectName']}"
        )
    if len(subjects) > 25:
        print(f"  ... +{len(subjects) - 25} more")

    fes = data.filtered("fixedEntry")
    print(f"\n=== fixedEntry texts ({len(fes)}) ===")
    text_count = Counter(f["fixedText"] for f in fes)
    print(json.dumps(dict(text_count), indent=2))


if __name__ == "__main__":
    main()
