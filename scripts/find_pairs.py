"""Inspect Taasika subjects to identify Lec+Lab/Tut pairs."""

from taasika_loader import load


def main() -> None:
    d = load(snapshot_id=240, tables=["subject"])
    subjects = d.filtered("subject")
    print(f"Total subjects: {len(subjects)}")

    by_short = {s["subjectShortName"]: s for s in subjects}

    print("\nLab/Tut subjects and their inferred base + matching Lec subject:")
    pairs: list[tuple[str, str]] = []
    standalone_labs: list[str] = []
    for s in subjects:
        sn = s["subjectShortName"] or ""
        if "lab" in sn.lower() or "tut" in sn.lower():
            base = (
                sn.replace("-Lab", "")
                .replace("Lab", "")
                .replace("-Tut", "")
                .replace("Tut", "")
                .replace("-Tutorial", "")
                .strip()
            )
            match = by_short.get(base)
            if match:
                pairs.append((match["subjectShortName"], sn))
                print(
                    f"  {sn:<20} -> {match['subjectShortName']:<20} "
                    f"(lec each={match['eachSlot']} n={match['nSlots']}; "
                    f"lab each={s['eachSlot']} n={s['nSlots']})"
                )
            else:
                standalone_labs.append(sn)
    print(f"\nTotal lec+lab/tut pairs found: {len(pairs)}")
    print(f"Standalone labs/tuts (no matching lec): {len(standalone_labs)}")
    for sn in standalone_labs[:20]:
        print(f"  - {sn}")

    print("\nKey subjects of interest:")
    for s in subjects:
        sn = (s["subjectShortName"] or "")
        fn = (s["subjectName"] or "").lower()
        if sn in ("CN", "CN-Lab", "SC", "SC-Lab", "OOP", "OOP-Lab", "DBMS", "DBMS-Lab"):
            print(f"  {s['subjectId']:>6} short={sn:<14} each={s['eachSlot']} n={s['nSlots']} batches={s['batches']} name={s['subjectName']}")
        elif "object oriented" in fn or "security in computing" in fn:
            print(f"  {s['subjectId']:>6} short={sn:<14} each={s['eachSlot']} n={s['nSlots']} batches={s['batches']} name={s['subjectName']}")


if __name__ == "__main__":
    main()
