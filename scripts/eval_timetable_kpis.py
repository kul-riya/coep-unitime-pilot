"""Evaluate a UniTime CSV timetable solution against unitime-out XML constraints.

Scores hard feasibility (coverage, patterns, conflicts, lunch, capacity),
preference accuracy (room hit rate, instructor match), and schedule efficiency
(load balance, travel, slot spread).

Usage (from repo root):
  python scripts/eval_timetable_kpis.py
  python scripts/eval_timetable_kpis.py --csv solutions/COEPSpr2026_v2.csv --out solutions/kpi_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "unitime-out"
DEFAULT_CSV = ROOT / "solutions" / "COEPSpr2026_v2.csv"
DEFAULT_OUT = ROOT / "solutions" / "kpi_report.json"

# UniTime day-code tokens, longest-first so "Th" / "Su" beat "T" / "S".
_DAY_TOKENS = ("MTWThFS", "MTWThF", "TThS", "MWF", "TTh", "SSu", "Th", "Su", "M", "T", "W", "F", "S")
_LUNCH_START = 12 * 60 + 30
_LUNCH_END = 13 * 60 + 30
_EARLY_END = 10 * 60 + 30
_LATE_START = 16 * 60 + 30
_EXAMPLE_LIMIT = 8


@dataclass
class OfferingClass:
    class_id: str
    subject: str
    course_nbr: str
    itype: str
    suffix: str
    limit: int
    preferred_rooms: list[str]  # "BUILDING ROOMNBR"
    instructor_id: str | None
    min_per_week: int
    time_pattern: str | None


@dataclass
class Meeting:
    weekday: str
    start: int  # minutes from midnight
    end: int


@dataclass
class Assignment:
    class_id: str
    subject: str
    course_nbr: str
    itype: str
    section: str
    date_pattern: str
    day_code: str
    start: int
    end: int
    duration: int
    room_key: str
    building: str
    room_nbr: str
    instructor_raw: str
    instructor_id: str | None
    meetings: list[Meeting]


@dataclass
class RoomInfo:
    key: str
    building: str
    room_nbr: str
    capacity: int
    external_id: str


@dataclass
class StaffMember:
    external_id: str
    first_name: str
    middle_name: str
    last_name: str
    csv_label: str


@dataclass
class KpiBucket:
    name: str
    checked: int = 0
    passed: int = 0
    examples: list[str] = field(default_factory=list)

    def record(self, ok: bool, example: str = "") -> None:
        self.checked += 1
        if ok:
            self.passed += 1
        elif example and len(self.examples) < _EXAMPLE_LIMIT:
            self.examples.append(example)

    @property
    def rate(self) -> float:
        return (100.0 * self.passed / self.checked) if self.checked else 100.0

    @property
    def failed(self) -> int:
        return self.checked - self.passed

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "checked": self.checked,
            "passed": self.passed,
            "failed": self.failed,
            "rate_pct": round(self.rate, 2),
            "examples": self.examples,
        }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


_COMPOUND_DAYS: dict[str, tuple[str, ...]] = {
    "MTWThFS": ("M", "T", "W", "Th", "F", "S"),
    "MTWThF": ("M", "T", "W", "Th", "F"),
    "TThS": ("T", "Th", "S"),
    "MWF": ("M", "W", "F"),
    "TTh": ("T", "Th"),
    "SSu": ("S", "Su"),
}


def _expand_days(code: str) -> list[str]:
    """Expand UniTime day codes (e.g. MWF, TTh, MTWThF) into weekday tokens."""
    remaining = code.strip()
    days: list[str] = []
    while remaining:
        matched = False
        for tok in _DAY_TOKENS:
            if remaining.startswith(tok):
                days.extend(_COMPOUND_DAYS.get(tok, (tok,)))
                remaining = remaining[len(tok) :]
                matched = True
                break
        if not matched:
            raise ValueError(f"unrecognized day code fragment in {code!r}: {remaining!r}")
    seen: set[str] = set()
    out: list[str] = []
    for d in days:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _parse_clock(text: str) -> int:
    """Parse UniTime CSV times like '3:30p', '8:30a', '12:30p' → minutes."""
    t = text.strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d{1,2}):(\d{2})([ap])", t)
    if not m:
        raise ValueError(f"bad time: {text!r}")
    hour = int(m.group(1))
    minute = int(m.group(2))
    ampm = m.group(3)
    if ampm == "a":
        if hour == 12:
            hour = 0
    else:
        if hour != 12:
            hour += 12
    return hour * 60 + minute


def _parse_hhmm(text: str) -> int:
    text = text.strip()
    if len(text) == 3:
        text = "0" + text
    return int(text[:2]) * 60 + int(text[2:])


def _overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def _parse_pattern(pattern: str) -> tuple[int, int]:
    """Return (meetings_per_week, minutes_per_meeting) from '3 x 60'."""
    m = re.fullmatch(r"(\d+)\s*x\s*(\d+)", pattern.strip())
    if not m:
        raise ValueError(f"bad time pattern: {pattern!r}")
    return int(m.group(1)), int(m.group(2))


def _fmt_mins(m: int) -> str:
    h, mi = divmod(m, 60)
    suffix = "a" if h < 12 or h == 24 else "p"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mi:02d}{suffix}"


def _staff_csv_label(first: str, middle: str, last: str) -> str:
    initials = first[:1].upper() if first else ""
    if middle:
        initials = f"{initials} {middle[:1].upper()}".strip()
    return f"{last}, {initials}".strip()


def _split_room(room_field: str) -> tuple[str, str]:
    parts = room_field.strip().split(None, 1)
    if len(parts) != 2:
        raise ValueError(f"bad ROOM field: {room_field!r}")
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_staff_indexes(path: Path) -> tuple[dict[str, StaffMember], dict[str, list[StaffMember]]]:
    root = ET.parse(path).getroot()
    by_id: dict[str, StaffMember] = {}
    by_label: dict[str, list[StaffMember]] = defaultdict(list)
    for sm in root.findall("staffMember"):
        member = StaffMember(
            external_id=sm.get("externalId", ""),
            first_name=sm.get("firstName", ""),
            middle_name=sm.get("middleName", ""),
            last_name=sm.get("lastName", ""),
            csv_label=_staff_csv_label(
                sm.get("firstName", ""), sm.get("middleName", ""), sm.get("lastName", "")
            ),
        )
        by_id[member.external_id] = member
        by_label[member.csv_label].append(member)
    return by_id, by_label


def load_rooms_from_buildings(path: Path) -> dict[str, RoomInfo]:
    """Load rooms keyed by 'BUILDING ROOMNBR' using building@abbreviation."""
    root = ET.parse(path).getroot()
    rooms: dict[str, RoomInfo] = {}
    for bld in root.findall("building"):
        building = bld.get("abbreviation") or bld.get("externalId") or ""
        for room in bld.findall("room"):
            nbr = room.get("roomNumber", "")
            key = f"{building} {nbr}"
            info = RoomInfo(
                key=key,
                building=building,
                room_nbr=nbr,
                capacity=int(room.get("capacity") or 0),
                external_id=room.get("externalId", ""),
            )
            rooms[key] = info
    return rooms


def load_preferences(path: Path) -> dict[tuple[str, str, str], str]:
    """(subject, course, type) → time pattern name."""
    root = ET.parse(path).getroot()
    out: dict[tuple[str, str, str], str] = {}
    for sp in root.findall("subpart"):
        tp = sp.find("timePref")
        if tp is None:
            continue
        key = (sp.get("subject", ""), sp.get("course", ""), sp.get("type", ""))
        out[key] = tp.get("pattern", "")
    return out


def load_offerings(
    path: Path, patterns: dict[tuple[str, str, str], str]
) -> dict[str, OfferingClass]:
    root = ET.parse(path).getroot()
    classes: dict[str, OfferingClass] = {}
    for offering in root.findall("offering"):
        course = offering.find("course")
        if course is None:
            continue
        subject = course.get("subject", "")
        course_nbr = course.get("courseNbr", "")
        for config in offering.findall("config"):
            min_by_type: dict[str, int] = {}
            for sp in config.findall("subpart"):
                min_by_type[sp.get("type", "")] = int(sp.get("minPerWeek") or 0)
            for cls in config.findall("class"):
                itype = cls.get("type", "")
                suffix = cls.get("suffix", "")
                class_id = cls.get("id") or f"{subject} {course_nbr} {itype} {suffix}"
                rooms = [
                    f"{r.get('building', '')} {r.get('roomNbr', '')}".strip()
                    for r in cls.findall("room")
                ]
                instr = None
                for ins in cls.findall("instructor"):
                    if ins.get("lead", "true").lower() == "true" or instr is None:
                        instr = ins.get("id")
                classes[class_id] = OfferingClass(
                    class_id=class_id,
                    subject=subject,
                    course_nbr=course_nbr,
                    itype=itype,
                    suffix=suffix,
                    limit=int(cls.get("limit") or 0),
                    preferred_rooms=rooms,
                    instructor_id=instr,
                    min_per_week=min_by_type.get(itype, 0),
                    time_pattern=patterns.get((subject, course_nbr, itype)),
                )
    return classes


def load_travel(path: Path) -> dict[tuple[str, str], int]:
    """Building→building travel minutes (min over representative room pairs)."""
    root = ET.parse(path).getroot()
    times: dict[tuple[str, str], int] = {}
    for fr in root.findall("from"):
        fb = fr.get("building", "")
        for to in fr.findall("to"):
            tb = to.get("building", "")
            mins = int((to.text or "0").strip() or 0)
            key = (fb, tb)
            if key not in times or mins < times[key]:
                times[key] = mins
    return times


def load_enrollments(path: Path) -> dict[str, list[str]]:
    """student externalId → list of class_ids."""
    root = ET.parse(path).getroot()
    out: dict[str, list[str]] = {}
    for st in root.findall("student"):
        sid = st.get("externalId", "")
        ids: list[str] = []
        for c in st.findall("class"):
            ids.append(
                f"{c.get('subject')} {c.get('courseNbr')} {c.get('type')} {c.get('suffix')}"
            )
        out[sid] = ids
    return out


def resolve_instructor(
    raw: str,
    by_label: dict[str, list[StaffMember]],
    expected_id: str | None,
    by_id: dict[str, StaffMember],
) -> str | None:
    candidates = by_label.get(raw, [])
    if expected_id and expected_id in by_id:
        expected_label = by_id[expected_id].csv_label
        if raw == expected_label:
            return expected_id
        # still prefer expected if it is among candidates
        for c in candidates:
            if c.external_id == expected_id:
                return expected_id
    if len(candidates) == 1:
        return candidates[0].external_id
    if len(candidates) > 1 and expected_id:
        for c in candidates:
            if c.external_id == expected_id:
                return expected_id
    if len(candidates) > 1:
        return candidates[0].external_id  # ambiguous
    return None


def load_assignments(
    path: Path,
    offerings: dict[str, OfferingClass],
    by_label: dict[str, list[StaffMember]],
    by_id: dict[str, StaffMember],
) -> list[Assignment]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assignments: list[Assignment] = []
    for row in rows:
        course = row["COURSE"].strip()
        itype = row["ITYPE"].strip()
        section = row["SECTION"].strip()
        class_id = f"{course} {itype} {section}"
        parts = course.split(None, 1)
        subject = parts[0] if parts else ""
        course_nbr = parts[1] if len(parts) > 1 else ""
        building, room_nbr = _split_room(row["ROOM"])
        start = _parse_clock(row["START_TIME"])
        end = _parse_clock(row["END_TIME"])
        day_code = row["DAY"].strip()
        days = _expand_days(day_code)
        meetings = [Meeting(d, start, end) for d in days]
        expected = offerings.get(class_id).instructor_id if class_id in offerings else None
        raw_instr = row["INSTRUCTOR"].strip()
        assignments.append(
            Assignment(
                class_id=class_id,
                subject=subject,
                course_nbr=course_nbr,
                itype=itype,
                section=section,
                date_pattern=row["DATE_PATTERN"].strip(),
                day_code=day_code,
                start=start,
                end=end,
                duration=end - start,
                room_key=f"{building} {room_nbr}",
                building=building,
                room_nbr=room_nbr,
                instructor_raw=raw_instr,
                instructor_id=resolve_instructor(raw_instr, by_label, expected, by_id),
                meetings=meetings,
            )
        )
    return assignments


# ---------------------------------------------------------------------------
# KPI computation
# ---------------------------------------------------------------------------


def _conflict_pairs(
    items: list[tuple[str, Meeting, str]],
) -> list[tuple[str, str, str]]:
    """items: (resource_key, meeting, class_id) → overlapping pairs of class ids."""
    by_res_day: dict[tuple[str, str], list[tuple[Meeting, str]]] = defaultdict(list)
    for key, meeting, class_id in items:
        by_res_day[(key, meeting.weekday)].append((meeting, class_id))
    conflicts: list[tuple[str, str, str]] = []
    for (key, _day), slots in by_res_day.items():
        slots.sort(key=lambda x: x[0].start)
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                a, id_a = slots[i]
                b, id_b = slots[j]
                if b.start >= a.end:
                    break
                if _overlaps(a.start, a.end, b.start, b.end):
                    conflicts.append((key, id_a, id_b))
    return conflicts


def evaluate(
    offerings: dict[str, OfferingClass],
    assignments: list[Assignment],
    rooms: dict[str, RoomInfo],
    travel: dict[tuple[str, str], int],
    enrollments: dict[str, list[str]],
    by_id: dict[str, StaffMember],
) -> dict[str, Any]:
    by_class = {a.class_id: a for a in assignments}

    coverage = KpiBucket("coverage")
    pattern = KpiBucket("time_pattern_fidelity")
    date_pat = KpiBucket("date_pattern")
    instr_id = KpiBucket("instructor_identity")
    capacity = KpiBucket("room_capacity")
    lunch = KpiBucket("lunch_weekend")
    room_pref = KpiBucket("room_preference")

    for class_id, off in offerings.items():
        a = by_class.get(class_id)
        has = (
            a is not None
            and bool(a.day_code)
            and bool(a.room_key)
            and a.end > a.start
        )
        coverage.record(has, f"missing assignment for {class_id}")
        if not has or a is None:
            continue

        # Date pattern
        date_pat.record(
            a.date_pattern == "Full Term",
            f"{class_id}: date_pattern={a.date_pattern!r}",
        )

        # Time pattern
        if off.time_pattern:
            try:
                n_meet, mins = _parse_pattern(off.time_pattern)
            except ValueError:
                pattern.record(False, f"{class_id}: bad required pattern {off.time_pattern}")
            else:
                ok = len(a.meetings) == n_meet and a.duration == mins
                pattern.record(
                    ok,
                    f"{class_id}: need {off.time_pattern}, got "
                    f"{len(a.meetings)}x{a.duration}min ({a.day_code} {_fmt_mins(a.start)}-{_fmt_mins(a.end)})",
                )
        else:
            pattern.record(False, f"{class_id}: no required pattern in preferences.xml")

        # Instructor identity
        if off.instructor_id:
            ok = a.instructor_id == off.instructor_id
            expected_label = (
                by_id[off.instructor_id].csv_label if off.instructor_id in by_id else off.instructor_id
            )
            instr_id.record(
                ok,
                f"{class_id}: expected {expected_label} ({off.instructor_id}), got {a.instructor_raw}",
            )

        # Capacity (skip UNAV/ONL from hard fail but still check when known)
        room = rooms.get(a.room_key)
        if a.building in ("UNAV", "ONL"):
            capacity.record(True)  # not counted as capacity violation
        elif room is None:
            capacity.record(False, f"{class_id}: unknown room {a.room_key}")
        else:
            ok = off.limit <= room.capacity
            capacity.record(
                ok,
                f"{class_id}: limit {off.limit} > capacity {room.capacity} ({a.room_key})",
            )

        # Lunch / weekend
        lunch_ok = True
        lunch_reason = ""
        for m in a.meetings:
            if m.weekday in ("S", "Su"):
                lunch_ok = False
                lunch_reason = f"{class_id}: weekend meeting on {m.weekday}"
                break
            if _overlaps(m.start, m.end, _LUNCH_START, _LUNCH_END):
                lunch_ok = False
                lunch_reason = (
                    f"{class_id}: overlaps lunch {_fmt_mins(m.start)}-{_fmt_mins(m.end)}"
                )
                break
        lunch.record(lunch_ok, lunch_reason)

        # Room preference
        if off.preferred_rooms:
            room_pref.record(
                a.room_key in off.preferred_rooms,
                f"{class_id}: {a.room_key} not in preferred {off.preferred_rooms}",
            )

    # Instructor / room conflicts
    instr_items: list[tuple[str, Meeting, str]] = []
    room_items: list[tuple[str, Meeting, str]] = []
    for a in assignments:
        key_i = a.instructor_id or f"raw:{a.instructor_raw}"
        for m in a.meetings:
            instr_items.append((key_i, m, a.class_id))
            room_items.append((a.room_key, m, a.class_id))

    instr_conflicts = _conflict_pairs(instr_items)
    room_conflicts = _conflict_pairs(room_items)

    instr_conflict_bucket = KpiBucket("instructor_double_booking")
    # one check per assignment-meeting pair that participates; simpler: check=1 per conflict opportunity
    # Report as: 0 conflicts = pass. Use number of assignments as denominator for rate.
    instr_conflict_bucket.checked = max(len(assignments), 1)
    instr_conflict_bucket.passed = instr_conflict_bucket.checked - min(
        len(instr_conflicts), instr_conflict_bucket.checked
    )
    for key, a, b in instr_conflicts[:_EXAMPLE_LIMIT]:
        instr_conflict_bucket.examples.append(f"instructor {key}: {a} overlaps {b}")

    room_conflict_bucket = KpiBucket("room_double_booking")
    room_conflict_bucket.checked = max(len(assignments), 1)
    room_conflict_bucket.passed = room_conflict_bucket.checked - min(
        len(room_conflicts), room_conflict_bucket.checked
    )
    for key, a, b in room_conflicts[:_EXAMPLE_LIMIT]:
        room_conflict_bucket.examples.append(f"room {key}: {a} overlaps {b}")

    # Student conflicts
    student_conflict_count = 0
    students_with_conflict = 0
    student_examples: list[str] = []
    for sid, class_ids in enrollments.items():
        meetings: list[tuple[Meeting, str]] = []
        for cid in class_ids:
            a = by_class.get(cid)
            if a is None:
                continue
            for m in a.meetings:
                meetings.append((m, cid))
        by_day: dict[str, list[tuple[Meeting, str]]] = defaultdict(list)
        for m, cid in meetings:
            by_day[m.weekday].append((m, cid))
        conflicted = False
        for day, slots in by_day.items():
            slots.sort(key=lambda x: x[0].start)
            for i in range(len(slots)):
                for j in range(i + 1, len(slots)):
                    ma, ca = slots[i]
                    mb, cb = slots[j]
                    if mb.start >= ma.end:
                        break
                    if _overlaps(ma.start, ma.end, mb.start, mb.end):
                        student_conflict_count += 1
                        conflicted = True
                        if len(student_examples) < _EXAMPLE_LIMIT:
                            student_examples.append(f"{sid} on {day}: {ca} overlaps {cb}")
        if conflicted:
            students_with_conflict += 1

    n_students = len(enrollments) or 1
    student_bucket = KpiBucket("student_conflicts")
    student_bucket.checked = n_students
    student_bucket.passed = n_students - students_with_conflict
    student_bucket.examples = student_examples

    # UNAV / ONL share
    unav_onl = sum(1 for a in assignments if a.building in ("UNAV", "ONL"))
    unav_rate = 100.0 * unav_onl / len(assignments) if assignments else 0.0

    # Instructor load (weekly contact minutes)
    load: dict[str, int] = defaultdict(int)
    for a in assignments:
        key = a.instructor_id or f"raw:{a.instructor_raw}"
        load[key] += a.duration * len(a.meetings)
    load_vals = list(load.values()) if load else [0]
    load_stats = {
        "instructors": len(load),
        "mean_minutes": round(statistics.mean(load_vals), 1),
        "stdev_minutes": round(statistics.pstdev(load_vals), 1) if len(load_vals) > 1 else 0.0,
        "max_minutes": max(load_vals),
        "min_minutes": min(load_vals),
    }

    # Travel feasibility + back-to-back density
    by_instr_day: dict[tuple[str, str], list[Assignment]] = defaultdict(list)
    for a in assignments:
        key = a.instructor_id or f"raw:{a.instructor_raw}"
        for m in a.meetings:
            # store a shallow view: use assignment with this day's window
            by_instr_day[(key, m.weekday)].append(a)

    travel_violations = 0
    travel_examples: list[str] = []
    adjacent_pairs = 0
    total_consec_pairs = 0
    default_travel = 5

    for (ikey, day), classes in by_instr_day.items():
        # unique by class_id, sort by start
        uniq = {c.class_id: c for c in classes}
        ordered = sorted(uniq.values(), key=lambda c: c.start)
        for i in range(len(ordered) - 1):
            a, b = ordered[i], ordered[i + 1]
            if b.start < a.end:
                continue  # overlap handled elsewhere
            gap = b.start - a.end
            total_consec_pairs += 1
            if gap == 0:
                adjacent_pairs += 1
            if a.building != b.building:
                needed = travel.get((a.building, b.building), default_travel)
                if gap < needed:
                    travel_violations += 1
                    if len(travel_examples) < _EXAMPLE_LIMIT:
                        travel_examples.append(
                            f"{ikey} on {day}: {a.class_id}@{a.building} → "
                            f"{b.class_id}@{b.building} gap={gap}min need≥{needed}"
                        )

    back_to_back_pct = (
        100.0 * adjacent_pairs / total_consec_pairs if total_consec_pairs else 0.0
    )

    # Slot spread
    early = mid = late = 0
    for a in assignments:
        for m in a.meetings:
            if m.end <= _EARLY_END:
                early += 1
            elif m.start >= _LATE_START:
                late += 1
            else:
                mid += 1
    total_meetings = early + mid + late or 1
    slot_spread = {
        "early_pct": round(100.0 * early / total_meetings, 2),
        "mid_pct": round(100.0 * mid / total_meetings, 2),
        "late_pct": round(100.0 * late / total_meetings, 2),
        "early": early,
        "mid": mid,
        "late": late,
        "total_meetings": early + mid + late,
    }

    hard_buckets = [
        coverage,
        pattern,
        date_pat,
        capacity,
        lunch,
        instr_conflict_bucket,
        room_conflict_bucket,
        student_bucket,
    ]
    # Equal-weight average so large buckets (e.g. students) do not dominate.
    hard_score = sum(b.rate for b in hard_buckets) / len(hard_buckets)
    hard_failed = sum(b.failed for b in hard_buckets)
    hard_checked = sum(b.checked for b in hard_buckets)

    pref_score = (room_pref.rate + instr_id.rate) / 2.0

    report: dict[str, Any] = {
        "summary": {
            "classes_in_offerings": len(offerings),
            "classes_in_solution": len(assignments),
            "hard_feasibility_score": round(hard_score, 2),
            "hard_checks": hard_checked,
            "hard_failures": hard_failed,
            "preference_score": round(pref_score, 2),
            "unav_onl_assignments": unav_onl,
            "unav_onl_pct": round(unav_rate, 2),
            "instructor_conflicts": len(instr_conflicts),
            "room_conflicts": len(room_conflicts),
            "student_conflict_pairs": student_conflict_count,
            "students_with_conflict": students_with_conflict,
            "students_total": len(enrollments),
            "travel_violations": travel_violations,
            "back_to_back_pct": round(back_to_back_pct, 2),
        },
        "hard": {b.name: b.as_dict() for b in hard_buckets},
        "preference": {
            room_pref.name: room_pref.as_dict(),
            instr_id.name: instr_id.as_dict(),
            "unav_onl": {
                "count": unav_onl,
                "pct": round(unav_rate, 2),
                "total_assignments": len(assignments),
            },
        },
        "efficiency": {
            "instructor_load": load_stats,
            "travel_violations": travel_violations,
            "travel_examples": travel_examples,
            "back_to_back_pct": round(back_to_back_pct, 2),
            "consecutive_pairs": total_consec_pairs,
            "adjacent_pairs": adjacent_pairs,
            "slot_spread": slot_spread,
        },
    }
    return report


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_bucket(b: dict[str, Any], indent: str = "  ") -> None:
    print(
        f"{indent}{b['name']:<28} "
        f"{b['passed']:>4}/{b['checked']:<4}  "
        f"{b['rate_pct']:6.1f}%  fail={b['failed']}"
    )
    for ex in b.get("examples") or []:
        print(f"{indent}  - {ex}")


def print_report(report: dict[str, Any]) -> None:
    s = report["summary"]
    print("=" * 64)
    print("Timetable KPI Report")
    print("=" * 64)
    print(
        f"Classes: offerings={s['classes_in_offerings']}  "
        f"solution={s['classes_in_solution']}"
    )
    print(f"Hard feasibility score : {s['hard_feasibility_score']:.1f} / 100")
    print(f"Preference score       : {s['preference_score']:.1f} / 100")
    print(
        f"Conflicts: instructor={s['instructor_conflicts']}  "
        f"room={s['room_conflicts']}  "
        f"students={s['students_with_conflict']}/{s['students_total']} "
        f"({s['student_conflict_pairs']} pairs)"
    )
    print(f"UNAV/ONL usage         : {s['unav_onl_assignments']} ({s['unav_onl_pct']:.1f}%)")
    print(f"Travel violations      : {s['travel_violations']}")
    print(f"Back-to-back density   : {s['back_to_back_pct']:.1f}%")
    print()
    print("Hard feasibility")
    for name, b in report["hard"].items():
        _print_bucket(b)
    print()
    print("Preference / soft accuracy")
    for name, b in report["preference"].items():
        if isinstance(b, dict) and "rate_pct" in b:
            _print_bucket(b)
        elif name == "unav_onl":
            print(
                f"  unav_onl                    "
                f"{b['count']:>4}/{b['total_assignments']:<4}  "
                f"{b['pct']:6.1f}%"
            )
    print()
    eff = report["efficiency"]
    load = eff["instructor_load"]
    print("Efficiency")
    print(
        f"  instructor load (min/wk)  "
        f"mean={load['mean_minutes']}  stdev={load['stdev_minutes']}  "
        f"min={load['min_minutes']}  max={load['max_minutes']}  "
        f"n={load['instructors']}"
    )
    spread = eff["slot_spread"]
    print(
        f"  slot spread               "
        f"early={spread['early_pct']}%  mid={spread['mid_pct']}%  "
        f"late={spread['late_pct']}%"
    )
    for ex in eff.get("travel_examples") or []:
        print(f"  - travel: {ex}")
    print("=" * 64)


def main(argv: list[str] | None = None) -> int:
    # PowerShell sessions on Windows commonly default to cp1252, which cannot
    # render the Unicode arrow used in travel examples. Keep report generation
    # independent of the active terminal code page.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="UniTime solution CSV")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="JSON report path")
    parser.add_argument(
        "--data-dir", type=Path, default=OUT_DIR, help="unitime-out directory"
    )
    args = parser.parse_args(argv)

    csv_path: Path = args.csv
    data_dir: Path = args.data_dir
    if not csv_path.is_file():
        print(f"ERROR: solution CSV not found: {csv_path}", file=sys.stderr)
        return 1

    patterns = load_preferences(data_dir / "preferences.xml")
    offerings = load_offerings(data_dir / "courseOffering.xml", patterns)
    rooms = load_rooms_from_buildings(data_dir / "buildingRoomImport.xml")
    by_id, by_label = load_staff_indexes(data_dir / "staff.xml")
    travel = load_travel(data_dir / "travelTimes.xml")
    enrollments = load_enrollments(data_dir / "studentenrollments.xml")
    assignments = load_assignments(csv_path, offerings, by_label, by_id)

    report = evaluate(offerings, assignments, rooms, travel, enrollments, by_id)
    report["meta"] = {
        "csv": str(csv_path),
        "data_dir": str(data_dir),
        "rooms_indexed": len(rooms),
        "staff": len(by_id),
        "enrolled_students": len(enrollments),
    }

    print_report(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
