"""Regenerate solutions/course_type_report.md from snapshot 240 + user rules."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taasika_loader import load
from classifications import year_classification, clean_course_title

OUT = Path(__file__).resolve().parent.parent / "solutions" / "course_type_report.md"

_LAB_SUFFIX = re.compile(
    r"(?:[\s_-]+)?(?:Lab(?:oratory)?|Tut(?:orial)?)\s*$",
    re.I,
)

# Lec/lab shortName mismatches in Taasika
_MANUAL_PAIRS = {
    "DE4-IBCS": "DE4-IBC-Lab",
    "AI": "AI-Lab",  # AI-Lab exists in subject table; force-include even if no SBT
    "MT-DL": "MTDL-Lab",
}

# Cross-department elective capacity (CSE dump only has 1 of each)
N_OE_OPTIONS = 5
N_MDM_OPTIONS = 5
MDM_YEARS = ("SY", "TY", "BT")
OE_YEARS = ("SY", "TY", "BT")


def year_for_subject(sid, sct, sbt, classes, batches, batch_to_classes) -> str:
    class_years = set()
    for r in sct:
        if r["subjectId"] == sid and r["classId"] in classes:
            c = classes[r["classId"]]
            class_years.add(year_classification(c["classShortName"], c["semester"])[0])
    if len(class_years) == 1:
        return next(iter(class_years))
    if class_years:
        return "/".join(sorted(class_years))

    by: set[str] = set()
    for r in sbt:
        if r["subjectId"] != sid:
            continue
        linked = {
            year_classification(classes[cid]["classShortName"], classes[cid]["semester"])[0]
            for cid in batch_to_classes.get(r["batchId"], [])
            if cid in classes
        }
        if len(linked) == 1:
            by.add(next(iter(linked)))
            continue
        b = batches.get(r["batchId"])
        if not b:
            continue
        name = (b["batchName"] or "").upper()
        for p in ("FY", "SY", "TY", "BT", "MT"):
            if name.startswith(p):
                by.add(p)
                break
    if len(by) == 1:
        return next(iter(by))
    return "/".join(sorted(by)) if by else "?"


def classify(short: str, name: str) -> str:
    t = f"{short} {name}".upper()
    sn = (short or "").upper()
    if "RESERVED" in t:
        return "RESERVED"
    if sn.startswith("PSEC") or "PSEC" in t:
        return "PSEC"
    if "HONOR" in t or "HONOUR" in t:
        return "HONOR"
    if "MINOR" in t:
        return "MINOR"
    if sn.startswith("MDM") or "MDM-" in sn:
        return "MDM"
    if sn.startswith("OE") or "OPEN ELECTIVE" in t:
        return "OE"
    if sn.startswith("DE"):
        return "DE"
    if sn.startswith("MT-") or "MTECH" in t.replace(" ", ""):
        return "MT-DEFAULT"
    return "DEFAULT"


def is_labish(short: str, batches_flag) -> bool:
    sn = (short or "").lower()
    return bool(batches_flag) or "lab" in sn or "tut" in sn


def base_short(short: str) -> str:
    return _LAB_SUFFIX.sub("", short or "").strip()


def pair_subjects(subjects: dict, offered: set[int]) -> dict:
    """Pair lec↔lab. Includes force pairs even if lab not in SCT/SBT."""
    by_short_all = {s["subjectShortName"]: s for s in subjects.values()}
    by_short_off = {
        s["subjectShortName"]: s
        for sid, s in subjects.items()
        if sid in offered
    }
    lec_to_lab: dict[int, int] = {}
    lab_to_lec: dict[int, int] = {}

    for sn, s in by_short_off.items():
        if not is_labish(sn, s.get("batches")):
            continue
        base = base_short(sn)
        if not base or base == sn:
            continue
        lec = by_short_off.get(base)
        if not lec:
            continue
        lec_to_lab[lec["subjectId"]] = s["subjectId"]
        lab_to_lec[s["subjectId"]] = lec["subjectId"]

    for lec_sn, lab_sn in _MANUAL_PAIRS.items():
        lec = by_short_all.get(lec_sn)
        lab = by_short_all.get(lab_sn)
        if not lec or not lab:
            continue
        if lec["subjectId"] not in offered and lec_sn not in _MANUAL_PAIRS:
            continue
        # Attach lab if lec is offered (lab may only exist in catalog)
        if lec["subjectId"] in offered:
            lec_to_lab[lec["subjectId"]] = lab["subjectId"]
            lab_to_lec[lab["subjectId"]] = lec["subjectId"]

    return {"lec_to_lab": lec_to_lab, "lab_to_lec": lab_to_lec}


def main() -> None:
    d = load(snapshot_id=240)
    subjects = {s["subjectId"]: s for s in d.filtered("subject")}
    classes = {c["classId"]: c for c in d.filtered("class")}
    batches = {b["batchId"]: b for b in d.filtered("batch")}
    batch_to_classes: dict[int, list[int]] = {}
    for bc in d.filtered("batchClass"):
        batch_to_classes.setdefault(bc["batchId"], []).append(bc["classId"])

    sct = d.filtered("subjectClassTeacher")
    sbt = d.filtered("subjectBatchTeacher")
    offered = {r["subjectId"] for r in sct} | {r["subjectId"] for r in sbt}
    pairs = pair_subjects(subjects, offered)

    # Rows: (year, course_cell, lab_cell, type, sort_key)
    rows: list[tuple[str, str, str, str, str]] = []
    consumed_labs: set[int] = set()

    for sid in sorted(offered):
        if sid in pairs["lab_to_lec"]:
            continue
        s = subjects[sid]
        short = s["subjectShortName"]
        typ = classify(short, s["subjectName"] or "")
        year = year_for_subject(sid, sct, sbt, classes, batches, batch_to_classes)

        lab_id = pairs["lec_to_lab"].get(sid)
        lab = subjects.get(lab_id) if lab_id else None
        if lab:
            consumed_labs.add(lab_id)
            y2 = year_for_subject(lab_id, sct, sbt, classes, batches, batch_to_classes)
            if year == "?" and y2 != "?":
                year = y2

        name = clean_course_title(s["subjectName"] or "").strip() or (s["subjectName"] or "").strip()
        lab_cell = "—"
        if lab:
            lab_note = ""
            if lab_id not in offered:
                lab_note = " *(forced: in catalog, no SCT/SBT in snap 240)*"
            lab_cell = f"`{lab['subjectShortName']}` — {(lab['subjectName'] or '').strip()}{lab_note}"

        # Special: DTL-Lab standalone → blank COURSE, name in LAB COURSE
        if short.upper() == "DTL-LAB" or (
            is_labish(short, s.get("batches"))
            and sid not in pairs["lab_to_lec"]
            and short.upper().startswith("DTL")
        ):
            course_cell = "—"
            lab_cell = f"`{short}` — {(s['subjectName'] or '').strip()}"
            typ = "DEFAULT"
        else:
            course_cell = f"`{short}` — {name}"

        rows.append((year, course_cell, lab_cell, typ, short))

    # Orphan offered labs not consumed (except DTL already handled as primary)
    for sid in sorted(offered):
        if sid not in pairs["lab_to_lec"]:
            continue
        if sid in consumed_labs:
            continue
        lab = subjects[sid]
        short = lab["subjectShortName"]
        if short.upper().startswith("DTL"):
            continue
        year = year_for_subject(sid, sct, sbt, classes, batches, batch_to_classes)
        typ = classify(short, lab["subjectName"] or "")
        rows.append(
            (
                year,
                "—",
                f"`{short}` — {(lab['subjectName'] or '').strip()}",
                typ,
                short,
            )
        )

    # Inject cross-dept OE / MDM placeholders so each year has 5 options
    def existing_codes(year: str, typ: str) -> list[str]:
        out = []
        for y, course, _lab, t, short in rows:
            if y == year and t == typ and course != "—":
                out.append(short)
        return out

    for year in MDM_YEARS:
        have = existing_codes(year, "MDM")
        need = N_MDM_OPTIONS - len(have)
        for i in range(need):
            n = len(have) + i + 1
            rows.append(
                (
                    year,
                    f"`MDM-OTHER-{n}` — *(other-dept MDM option {n}; not in CSE dump)*",
                    "—",
                    "MDM",
                    f"MDM-OTHER-{n}",
                )
            )

    for year in OE_YEARS:
        have = existing_codes(year, "OE")
        need = N_OE_OPTIONS - len(have)
        for i in range(need):
            n = len(have) + i + 1
            rows.append(
                (
                    year,
                    f"`OE-OTHER-{n}` — *(other-dept OE option {n}; not in CSE dump)*",
                    "—",
                    "OE",
                    f"OE-OTHER-{n}",
                )
            )

    order = {"FY": 0, "SY": 1, "TY": 2, "BT": 3, "MT": 4}
    type_order = {
        "DEFAULT": 0,
        "RESERVED": 1,
        "DE": 2,
        "OE": 3,
        "MDM": 4,
        "HONOR": 5,
        "MINOR": 6,
        "PSEC": 7,
        "MT-DEFAULT": 8,
    }
    rows.sort(
        key=lambda r: (
            order.get(r[0].split("/")[0], 9),
            r[0],
            type_order.get(r[3], 9),
            r[4],
        )
    )

    lines = [
        "# Course type report (snapshot 240) — revised",
        "",
        "## Student body (planned)",
        "",
        "| Cohort | Count |",
        "|--------|------:|",
        "| FY CSE | 400 |",
        "| FY AIML | 100 |",
        "| SY CSE | 400 |",
        "| SY AIML | 100 |",
        "| TY CSE | 400 |",
        "| TY AIML | 100 |",
        "| BT CSE | 400 |",
        "| BT AIML | 100 |",
        "| **B.Tech subtotal** | **2000** |",
        "| MT (programs in dump) | *existing MT class sizes / TBD* |",
        "",
        "**CSE vs AIML:** same course basket (same curriculum; cohort name differs).",
        "",
        "## Enrollment rules (planned)",
        "",
        "1. Every student takes all **DEFAULT** + **RESERVED** courses for their year.",
        "2. For each elective group present that year, every student **picks exactly one** option; options split as evenly as possible.",
        "3. Elective groups can stack (e.g. TY: one DE + one MDM + one OE).",
        "4. **HONOR** / **MINOR** (BT): every student picks one from that group.",
        "5. **OE** and **MDM** are college-wide: assume **~5 options across departments** (CSE dump shows 1; remaining are placeholders). Equal split across all 5.",
        "6. **MDM** and **OE** apply to **SY, TY, and BT** (not FY).",
        "",
        "## Hard-coded shared time slots (college-wide)",
        "",
        "| TYPE | Days | Time | Notes |",
        "|------|------|------|-------|",
        "| **MDM** | Mon & Tue | **16:30–18:30** | Same slot for all MDM options / all depts; SY+TY+BT |",
        "| **OE** | Wed & Thu | **16:30–17:30** | Same slot for all OE options / all depts; SY+TY+BT |",
        "| **DE** | *(solver chooses one fixed pattern)* | Same meeting time for **all DE options** in a year (mutually exclusive pick) |",
        "",
        "## Course table",
        "",
        "| YEAR | COURSE | LAB COURSE | TYPE |",
        "|------|--------|------------|------|",
    ]

    for year, course, lab, typ, _short in rows:
        lines.append(f"| {year} | {course} | {lab} | **{typ}** |")

    lines += [
        "",
        "## Counts by year × type",
        "",
        "| YEAR | TYPE | N |",
        "|------|------|---|",
    ]
    counts = Counter((r[0], r[3]) for r in rows)
    for (y, t), n in sorted(
        counts.items(),
        key=lambda x: (order.get(x[0][0].split("/")[0], 9), x[0][0], type_order.get(x[0][1], 9)),
    ):
        lines.append(f"| {y} | {t} | {n} |")

    # Equal-split preview for electives
    lines += [
        "",
        "## Equal-split preview (500 students / B.Tech year)",
        "",
        "| YEAR | Group | # options | Students / option (approx) |",
        "|------|-------|----------:|---------------------------:|",
    ]
    for year in ("FY", "SY", "TY", "BT"):
        by_type: dict[str, int] = Counter(r[3] for r in rows if r[0] == year)
        for typ in ("DE", "OE", "MDM", "HONOR", "MINOR"):
            n = by_type.get(typ, 0)
            if n == 0:
                continue
            lines.append(f"| {year} | {typ} | {n} | {500 // n} (rem {500 % n}) |")

    lines += [
        "",
        "## Notes",
        "",
        "- `AI-Lab` is attached to `AI` per your instruction. In snapshot 240 it exists in `subject` but has **no** `subjectClassTeacher` / `subjectBatchTeacher` / `timeTable` row — flagged in the LAB column.",
        "- `DTL-Lab`: COURSE blank; name only under LAB COURSE.",
        "- `OE-OTHER-*` / `MDM-OTHER-*` are placeholders for other-department electives (avg 5 college-wide).",
        "- M.Tech rows included; PSEC treated as MT elective picks (one per PSEC level if you confirm later).",
        "",
        "**Waiting for your OK before rewriting `studentenrollments.xml` / preferences.**",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"{'YEAR':4} | {'COURSE':28} | {'LAB':24} | TYPE")
    print("-" * 80)
    for year, course, lab, typ, short in rows:
        c = short if course != "—" else "(blank)"
        l = "—"
        if lab != "—":
            l = lab.split(" — ")[0].strip("`")
        print(f"{year:4} | {c:28} | {l:24} | {typ}")


if __name__ == "__main__":
    main()
