"""Confirmed student intake and room-block rules for the UniTime session.

CSE FY is 160 (regular first-year). Direct Second Year (DSY) join in SY,
so SY/TY/BT CSE is 200 in two divisions of 100. AIML is a separate 100
students per year on the same course basket. M.Tech counts stay as in
the Taasika dump.
"""

from __future__ import annotations

import math
from typing import Sequence


# CSE headcount by year. FY is smaller because DSY students appear in SY.
N_CSE: dict[str, int] = {
    "FY": 160,
    "SY": 200,
    "TY": 200,
    "BT": 200,
}
N_AIML = 100
N_DIVISIONS = 2  # SY / TY / BT lecture divisions

# Other-department room blocks (no CSE/AIML enrollments).
MDM_BLOCK_SEATS = 100
MDM_LEC_MIN_PER_WEEK = 240  # 2 x 120
OE_BLOCK_SEATS = 100
OE_LEC_MIN_PER_WEEK = 120  # 2-credit OE: 2 hours on any 2 weekdays

# BT/TY departmental electives: equal split of the year across options.
N_DE2_OPTIONS = 3
N_DE4_OPTIONS = 3


def year_headcount(year_key: str) -> int:
    """CSE + AIML students for a B.Tech year (M.Tech is separate)."""
    return N_CSE.get(year_key, 0) + (N_AIML if year_key in N_CSE else 0)


def cse_count(year_key: str) -> int:
    return N_CSE.get(year_key, 0)


def is_mdm_subject(short_name: str) -> bool:
    sn = (short_name or "").upper()
    return sn.startswith("MDM") or "MDM-" in sn


def is_oe_subject(short_name: str) -> bool:
    sn = (short_name or "").upper()
    return sn.startswith("OE") or sn.startswith("OE-")


def is_de_subject(short_name: str) -> bool:
    return (short_name or "").upper().startswith("DE")


def year_from_note(note: str) -> str | None:
    n = (note or "").upper()
    for y in ("FY", "SY", "TY", "BT", "MT"):
        if n.startswith(y):
            return y
    return None


def year_from_notes(notes: Sequence[str]) -> str | None:
    years = {year_from_note(n) for n in notes}
    years.discard(None)
    if len(years) == 1:
        return next(iter(years))
    return None


def spread_demand(n_sections: int, demand: int, current: Sequence[int]) -> list[int]:
    """Raise section limits so they cover ``demand``, never shrinking a seat that already exists.

    If current total already covers demand, keep Taasika sizes. Otherwise each
    section becomes at least ``ceil(demand / n_sections)``.
    """
    if n_sections <= 0:
        return list(current)
    cur = [int(x or 0) for x in current]
    if sum(cur) >= demand:
        return cur
    base = math.ceil(demand / n_sections)
    return [max(c, base) for c in cur]


def even_split(n_sections: int, demand: int) -> list[int]:
    """Split ``demand`` as evenly as possible across ``n_sections`` (may shrink)."""
    if n_sections <= 0:
        return []
    q, r = divmod(demand, n_sections)
    return [q + (1 if i < r else 0) for i in range(n_sections)]
