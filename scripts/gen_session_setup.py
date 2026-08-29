"""Generate sessionSetup.xml for UniTime (Even Sem 25-26 / snapshot 240)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from taasika_loader import load
from xml_common import LICENSE_HEADER, fmt_date, week_ranges, xml_escape
from classifications import (
    DEPARTMENT_LABELS,
    SUBJECT_AREAS,
    department_code,
    subject_area,
)


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026

SESSION_START = date(2026, 1, 19)
CLASS_END = date(2026, 4, 30)
EXAM_START = date(2026, 5, 4)
SESSION_END = date(2026, 5, 22)
EVENT_START = date(2026, 1, 1)
EVENT_END = date(2026, 6, 15)

HOLIDAYS: list[date] = [
    date(2026, 1, 26),
    date(2026, 3, 3),
    date(2026, 3, 14),
    date(2026, 4, 3),
    date(2026, 4, 14),
    date(2026, 5, 1),
]

DAY_BEGIN_MIN = 8 * 60 + 30
SLOTS_PER_DAY = 10  # 08:30 to 18:30 (10 x 60-minute slots)
SLOT_MIN = 60


def _slot_starts(num_slots: int = SLOTS_PER_DAY) -> list[str]:
    out: list[str] = []
    for i in range(num_slots):
        minute = DAY_BEGIN_MIN + i * SLOT_MIN
        h, m = divmod(minute, 60)
        out.append(f"{h:02d}{m:02d}")
    return out


# Day codes UniTime may assign; each pattern only gets codes whose
# meeting count equals nbrMeetings (e.g. "2 x 60" → MW, TTh, never MWF).
_DAY_CODE_CATALOG: list[str] = [
    "M", "T", "W", "Th", "F",
    "MW", "MF", "WF", "TTh", "MT", "MTh", "TF", "WTh", "ThF",
    "MWF", "MThF", "MTW", "MTF", "MWTh", "WThF",
    "MTWTh", "MTWF", "MTThF", "MWThF", "TWThF",
    "MTWThF",
]
_DAY_PARSE_TOKENS = ("Th", "M", "T", "W", "F")
_WEEKEND_TOKENS = {"S", "Su"}


def _meeting_count(code: str) -> int:
    remaining = code
    count = 0
    while remaining:
        for tok in _DAY_PARSE_TOKENS:
            if remaining.startswith(tok):
                count += 1
                remaining = remaining[len(tok) :]
                break
        else:
            raise ValueError(f"unrecognized day code: {code!r}")
    return count


def _has_weekend(code: str) -> bool:
    remaining = code
    while remaining:
        matched = False
        for tok in ("Th", "Su", "M", "T", "W", "F", "S"):
            if remaining.startswith(tok):
                if tok in _WEEKEND_TOKENS:
                    return True
                remaining = remaining[len(tok) :]
                matched = True
                break
        if not matched:
            break
    return False


def _day_codes_for_meetings(nbr_meetings: int) -> list[str]:
    return [
        c
        for c in _DAY_CODE_CATALOG
        if _meeting_count(c) == nbr_meetings and not _has_weekend(c)
    ]


def _header() -> str:
    return (
        f'<sessionSetup term="{TERM}" year="{YEAR}" campus="{CAMPUS}" '
        f'dateFormat="yyyy/M/d" created="Generated from Taasika snapshot 240">\n'
    )


def _session_block() -> str:
    holiday_lines = "\n".join(
        f'    <holiday date="{fmt_date(h)}"/>' for h in HOLIDAYS
    )
    return (
        f'  <session startDate="{fmt_date(SESSION_START)}" endDate="{fmt_date(SESSION_END)}" '
        f'classEndDate="{fmt_date(CLASS_END)}" examStartDate="{fmt_date(EXAM_START)}" '
        f'eventStartDate="{fmt_date(EVENT_START)}" eventEndDate="{fmt_date(EVENT_END)}">\n'
        f'  <holidays>\n'
        f'{holiday_lines}\n'
        f'  </holidays>\n'
        f'  </session>\n'
    )


def _managers_block() -> str:
    return (
        '  <managers incremental="true">\n'
        '    <manager externalId="taasika-admin" firstName="Taasika" lastName="Admin" email="admin@unitime.local">\n'
        '      <department code="0101"/>\n'
        '      <role reference="Administrator" primary="true" emails="true"/>\n'
        '    </manager>\n'
        '    <manager externalId="cse-sched-mgr" firstName="CSE" lastName="Scheduler" email="cse-sched@unitime.local">\n'
        '      <department code="0101"/>\n'
        '      <department code="0104"/>\n'
        '      <role reference="Dept Sched Mgr" primary="true" emails="true"/>\n'
        '    </manager>\n'
        '    <manager externalId="entc-sched-mgr" firstName="ENTC" lastName="Scheduler" email="entc-sched@unitime.local">\n'
        '      <department code="0102"/>\n'
        '      <role reference="Dept Sched Mgr" primary="true" emails="true"/>\n'
        '    </manager>\n'
        '    <manager externalId="instru-sched-mgr" firstName="Instru" lastName="Scheduler" email="instru-sched@unitime.local">\n'
        '      <department code="0103"/>\n'
        '      <role reference="Dept Sched Mgr" primary="true" emails="true"/>\n'
        '    </manager>\n'
        '  </managers>\n'
    )


def _departments_block(depts) -> str:
    lines: list[str] = ['  <departments>']
    for dept in depts:
        code = department_code(dept["deptId"])
        label = DEPARTMENT_LABELS[code]
        external_id = f"taasika-dept-{dept['deptId']}"
        lines.append(
            f'    <department code="{code}" externalId="{external_id}" '
            f'abbreviation="{xml_escape(label["abbreviation"])}" name="{xml_escape(label["name"])}">'
        )
        lines.append('      <eventManagement enabled="true"/>')
        lines.append('      <required time="false" room="false" distribution="false"/>')
        lines.append('      <instructorPreferences inherit="true"/>')
        lines.append('    </department>')
    lines.append('  </departments>\n')
    return "\n".join(lines)


def _subject_areas_block(subjects) -> str:
    in_use: set[str] = set()
    for s in subjects:
        in_use.add(subject_area(s.get("subjectShortName", ""), s.get("subjectName", "")))
    lines: list[str] = ['  <subjectAreas>']
    for code, meta in SUBJECT_AREAS.items():
        if code not in in_use:
            continue
        lines.append(
            f'    <subjectArea abbreviation="{xml_escape(code)}" '
            f'title="{xml_escape(meta["title"])}" department="{meta["department"]}"/>'
        )
    lines.append('  </subjectAreas>\n')
    return "\n".join(lines)


def _solver_groups_block() -> str:
    return (
        '  <solverGroups>\n'
        '    <solverGroup abbreviation="CSE" name="CSE Course Timetabling">\n'
        '      <manager externalId="cse-sched-mgr"/>\n'
        '      <department code="0101"/>\n'
        '      <department code="0104"/>\n'
        '    </solverGroup>\n'
        '    <solverGroup abbreviation="ENTC" name="ENTC Course Timetabling">\n'
        '      <manager externalId="entc-sched-mgr"/>\n'
        '      <department code="0102"/>\n'
        '    </solverGroup>\n'
        '    <solverGroup abbreviation="INSTRU" name="Instrumentation Course Timetabling">\n'
        '      <manager externalId="instru-sched-mgr"/>\n'
        '      <department code="0103"/>\n'
        '    </solverGroup>\n'
        '  </solverGroups>\n'
    )


def _date_patterns_block() -> str:
    weeks = week_ranges(SESSION_START, CLASS_END, off_days=HOLIDAYS)
    lines: list[str] = ['  <datePatterns>']
    lines.append('    <datePattern name="Full Term" type="Standard" visible="true" default="true">')
    for (a, b) in weeks:
        lines.append(f'      <dates fromDate="{fmt_date(a)}" toDate="{fmt_date(b)}"/>')
    lines.append('    </datePattern>')
    lines.append('    <datePattern name="Exam Period" type="Non-standard" visible="true" default="false">')
    lines.append(f'      <dates fromDate="{fmt_date(EXAM_START)}" toDate="{fmt_date(SESSION_END)}"/>')
    lines.append('    </datePattern>')
    lines.append('  </datePatterns>\n')
    return "\n".join(lines)


def _time_patterns_block() -> str:
    starts = _slot_starts()

    patterns: list[tuple[str, int, int]] = [
        ("1 x 60", 1, 60),
        ("2 x 60", 2, 60),
        ("3 x 60", 3, 60),
        ("4 x 60", 4, 60),
        ("5 x 60", 5, 60),
        ("1 x 120", 1, 120),
        ("2 x 120", 2, 120),
        ("1 x 180", 1, 180),
        ("1 x 480 Project", 1, 480),
        ("Exact Time", 1, 0),
    ]

    lines: list[str] = ['  <timePatterns>']
    for name, nbr_meetings, mins_per_meeting in patterns:
        if name == "Exact Time":
            lines.append(
                f'    <timePattern name="{name}" nbrMeetings="{nbr_meetings}" '
                f'minsPerMeeting="{mins_per_meeting}" type="Exact Time" visible="true" '
                f'nbrSlotsPerMeeting="6" breakTime="0"/>'
            )
            continue
        slots_per_meeting = max(1, mins_per_meeting // 5)
        day_codes = _day_codes_for_meetings(nbr_meetings)
        if not day_codes:
            raise ValueError(
                f"no day codes with {nbr_meetings} meetings for pattern {name!r}"
            )
        lines.append(
            f'    <timePattern name="{name}" nbrMeetings="{nbr_meetings}" '
            f'minsPerMeeting="{mins_per_meeting}" type="Standard" visible="true" '
            f'nbrSlotsPerMeeting="{slots_per_meeting}" breakTime="0">'
        )
        for d in day_codes:
            lines.append(f'      <days code="{d}"/>')
        max_start_idx = max(0, SLOTS_PER_DAY - (mins_per_meeting // SLOT_MIN))
        for idx in range(max_start_idx + 1):
            if idx >= len(starts):
                break
            lines.append(f'      <time start="{starts[idx]}"/>')
        lines.append('    </timePattern>')
    lines.append('  </timePatterns>\n')
    return "\n".join(lines)


def _exam_periods_block() -> str:
    lines: list[str] = ['  <examinationPeriods>', '    <periods type="final">']
    d = EXAM_START
    while d <= SESSION_END:
        if d.weekday() != 6:
            lines.append(f'      <period date="{fmt_date(d)}" startTime="0900" length="180"/>')
            lines.append(f'      <period date="{fmt_date(d)}" startTime="1400" length="180"/>')
        d = d.fromordinal(d.toordinal() + 1)
    lines.append('    </periods>')
    lines.append('  </examinationPeriods>\n')
    return "\n".join(lines)


def main() -> None:
    data = load(snapshot_id=240, tables=["dept", "subject", "config"])
    depts = sorted(data.rows("dept"), key=lambda d: d["deptId"])
    subjects = data.filtered("subject")

    out: list[str] = [LICENSE_HEADER, _header()]
    out.append(_session_block())
    out.append(_managers_block())
    out.append(_departments_block(depts))
    out.append(_subject_areas_block(subjects))
    out.append(_solver_groups_block())
    out.append(_date_patterns_block())
    out.append(_time_patterns_block())
    out.append(_exam_periods_block())
    out.append("</sessionSetup>\n")

    target = Path(__file__).resolve().parent.parent / "unitime-out" / "sessionSetup.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(out), encoding="utf-8")
    numbered = Path(__file__).resolve().parent.parent / "unitime-out" / "1sessionSetup.xml"
    numbered.write_text("".join(out), encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
