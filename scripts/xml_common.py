"""Helpers shared by every UniTime XML generator script."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable, Tuple


LICENSE_HEADER = (
    "<!--\n"
    "  Generated from the Taasika SQL dump (snapshot 240, 'published-19jan26').\n"
    "  Source schema: taasika2-foss-26jan26.sql\n"
    "  Template reference: samplexml/ (UniTime XML interface)\n"
    "  See: https://www.unitime.org/uct_interfaces.php\n"
    "-->\n"
)


def xml_escape(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slugify(value: str, max_len: int = 32) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value or "")
    cleaned = cleaned.strip("-")
    return cleaned[:max_len] or "x"


def week_ranges(start: date, end: date, off_days: Iterable[date] = ()) -> list[Tuple[date, date]]:
    """Yield contiguous (mon..sun) week chunks excluding ``off_days``.

    UniTime stores instructional weeks as a list of ``<dates fromDate="" toDate=""/>``
    intervals.  This helper walks Monday-anchored weeks and emits one or more
    sub-intervals per week so that holidays are excluded.
    """
    off = {d for d in off_days}
    out: list[Tuple[date, date]] = []
    cur = start - timedelta(days=start.weekday())
    while cur <= end:
        week_end = cur + timedelta(days=6)
        seg_start: date | None = None
        for offset in range(7):
            day = cur + timedelta(days=offset)
            if day < start or day > end or day in off:
                if seg_start is not None:
                    out.append((seg_start, day - timedelta(days=1)))
                    seg_start = None
                continue
            if seg_start is None:
                seg_start = day
        if seg_start is not None:
            out.append((seg_start, week_end if week_end <= end else end))
        cur += timedelta(days=7)
    return out


def fmt_date(d: date) -> str:
    return f"{d.year}/{d.month}/{d.day}"


def fmt_date_iso(d: date) -> str:
    return d.isoformat()
