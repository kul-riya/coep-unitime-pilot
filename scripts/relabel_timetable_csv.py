"""Relabel UniTime timetable CSV COURSE column from old numeric nbrs to short codes.

Also writes a simple printable HTML timetable grid using the short codes.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taasika_loader import load
from classifications import find_course_pairs, subject_area
from gen_course_catalog import course_number_from_short

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "solutions"
DEFAULT_CSV = OUT / "COEPSpr2026_v4.csv"


def build_old_to_new() -> dict[str, str]:
    """Replay pre-shortName numbering (per-area from 101) → short courseNbr."""
    data = load(snapshot_id=240, tables=["subject"])
    subjects = sorted(data.filtered("subject"), key=lambda s: s["subjectId"])
    lab_to_lec = find_course_pairs(subjects)["lab_to_lec"]

    counters: dict[str, int] = {}
    used: set[str] = set()
    mapping: dict[str, str] = {}
    detail: dict[str, str] = {}

    for s in subjects:
        sid = s["subjectId"]
        if sid in lab_to_lec:
            continue
        area = subject_area(s["subjectShortName"], s["subjectName"])
        counters.setdefault(area, 100)
        counters[area] += 1
        old_nbr = str(counters[area])
        new_nbr = course_number_from_short(s["subjectShortName"] or "", sid, used)
        old_key = f"{area} {old_nbr}"
        new_key = f"{area} {new_nbr}"
        mapping[old_key] = new_key
        detail[old_key] = s["subjectShortName"] or new_nbr
    return mapping


def relabel_csv(src: Path, dst: Path, mapping: dict[str, str]) -> tuple[int, int]:
    with src.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    changed = 0
    unknown: set[str] = set()
    for row in rows:
        course = (row.get("COURSE") or "").strip()
        if course in mapping:
            if mapping[course] != course:
                changed += 1
            row["COURSE"] = mapping[course]
        elif course and not any(
            course.endswith(f" {code}") or course.split(" ", 1)[-1] == code
            for code in ("CN", "AI", "CO", "CoI")  # already short?
        ):
            # already short if second token is non-numeric
            parts = course.split(" ", 1)
            if len(parts) == 2 and not parts[1].isdigit():
                pass  # already labeled
            else:
                unknown.add(course)

    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    if unknown:
        print(f"WARNING: {len(unknown)} COURSE values not in map (left unchanged):")
        for u in sorted(unknown)[:20]:
            print(f"  {u}")
    return changed, len(rows)


def _parse_time(t: str) -> int:
    """Return minutes from midnight for UniTime-style '3:30p'."""
    t = (t or "").strip().lower()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*([ap])m?$", t)
    if not m:
        return 0
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return h * 60 + mi


def write_html(csv_path: Path, html_path: Path) -> None:
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    # Expand day codes into per-day meetings
    day_tokens = ("MTWThFS", "MTWThF", "TThS", "MWF", "TTh", "Th", "Su", "M", "T", "W", "F", "S")
    order = ["M", "T", "W", "Th", "F", "S"]
    labels = {
        "M": "Monday",
        "T": "Tuesday",
        "W": "Wednesday",
        "Th": "Thursday",
        "F": "Friday",
        "S": "Saturday",
    }

    def expand(code: str) -> list[str]:
        rem = code or ""
        out: list[str] = []
        while rem:
            for tok in day_tokens:
                if rem.startswith(tok):
                    if tok == "MTWThFS":
                        out.extend(["M", "T", "W", "Th", "F", "S"])
                    elif tok == "MTWThF":
                        out.extend(["M", "T", "W", "Th", "F"])
                    elif tok == "TThS":
                        out.extend(["T", "Th", "S"])
                    elif tok == "MWF":
                        out.extend(["M", "W", "F"])
                    elif tok == "TTh":
                        out.extend(["T", "Th"])
                    else:
                        out.append(tok)
                    rem = rem[len(tok) :]
                    break
            else:
                rem = rem[1:]
        return out

    # slots 08:30 .. 19:30 hourly
    slot_starts = list(range(8 * 60 + 30, 19 * 60 + 30, 60))

    def fmt(mins: int) -> str:
        h, m = divmod(mins, 60)
        ap = "am" if h < 12 else "pm"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d}{ap}"

    # grid[day][slot_start] = list of labels
    grid: dict[str, dict[int, list[str]]] = {d: defaultdict(list) for d in order}

    for row in rows:
        course = row["COURSE"].strip()
        # Prefer short code only for display: "CS CN" -> "CN"
        short = course.split(" ", 1)[-1] if " " in course else course
        itype = row["ITYPE"].strip()
        sec = row["SECTION"].strip()
        room = (row.get("ROOM") or "").strip()
        label = f"{short} {itype}{sec}"
        if room:
            label += f" @ {room.split()[-1]}"
        start = _parse_time(row["START_TIME"])
        end = _parse_time(row["END_TIME"])
        for day in expand(row["DAY"]):
            if day not in grid:
                continue
            for s in slot_starts:
                if start <= s < end:
                    grid[day][s].append(label)

    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>",
        "<title>COEP Timetable (subject codes)</title>",
        "<style>",
        "body{font-family:Segoe UI,Arial,sans-serif;margin:16px;}",
        "h1{font-size:1.2rem;} table{border-collapse:collapse;width:100%;font-size:11px;}",
        "th,td{border:1px solid #ccc;padding:4px;vertical-align:top;}",
        "th{background:#1e3a5f;color:#fff;} td{min-width:90px;}",
        ".cell div{margin:2px 0;padding:2px 4px;background:#e8f1ff;border-radius:3px;}",
        "</style></head><body>",
        "<h1>COEP Spr 2026 - timetable with subject codes</h1>",
        f"<p>Source: {csv_path.name}</p>",
        "<table><thead><tr><th>Time</th>",
    ]
    for d in order:
        lines.append(f"<th>{labels[d]}</th>")
    lines.append("</tr></thead><tbody>")

    for s in slot_starts:
        lines.append(f"<tr><th>{fmt(s)}</th>")
        for d in order:
            cells = grid[d].get(s, [])
            inner = "".join(f"<div>{c}</div>" for c in cells) or "&nbsp;"
            lines.append(f"<td class='cell'>{inner}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table></body></html>")
    html_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    mapping = build_old_to_new()
    (OUT / "course_nbr_map.json").write_text(
        json.dumps(mapping, indent=2), encoding="utf-8"
    )

    coded = OUT / "COEPSpr2026_v4_coded.csv"
    changed, total = relabel_csv(src, coded, mapping)

    # Also refresh the primary v4 export so KPIs / PDF consumers see short codes.
    backup = OUT / "COEPSpr2026_v4_numeric.csv"
    if not backup.exists():
        backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.write_text(coded.read_text(encoding="utf-8"), encoding="utf-8")

    html = OUT / "timetable_v4.html"
    write_html(src, html)

    print(f"mapped {changed}/{total} COURSE rows")
    print(f"wrote {coded.relative_to(ROOT)}")
    print(f"wrote {backup.relative_to(ROOT)} (original numeric backup)")
    print(f"updated {src.relative_to(ROOT)} with subject codes")
    print(f"wrote {html.relative_to(ROOT)}")
    print(f"wrote solutions/course_nbr_map.json ({len(mapping)} offerings)")


if __name__ == "__main__":
    main()
