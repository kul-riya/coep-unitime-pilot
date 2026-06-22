"""Domain rules to map Taasika rows to UniTime classifications.

Centralising the heuristics here keeps every XML generator consistent.
"""

from __future__ import annotations

import re
from typing import Dict, Optional


SUBJECT_AREAS: Dict[str, Dict[str, str]] = {
    "CS": {
        "title": "Computer Science and Engineering",
        "department": "0101",
    },
    "MT": {
        "title": "M.Tech Programs (CSE, IS, AI, DS)",
        "department": "0101",
    },
    "IFC": {
        "title": "Interdisciplinary Foundation Courses",
        "department": "0101",
    },
    "VSEC": {
        "title": "Vocational Skill Enhancement Courses",
        "department": "0101",
    },
}


DEPARTMENT_CODES: Dict[int, str] = {
    1: "0101",
    2: "0102",
    3: "0103",
    4: "0104",
}


DEPARTMENT_LABELS: Dict[str, Dict[str, str]] = {
    "0101": {
        "abbreviation": "CSE",
        "name": "Computer Science and Engineering (CEIT)",
    },
    "0102": {
        "abbreviation": "ENTC",
        "name": "Electronics and Telecommunication Engineering",
    },
    "0103": {
        "abbreviation": "INSTRU",
        "name": "Instrumentation Engineering",
    },
    "0104": {
        "abbreviation": "IT",
        "name": "Information Technology (CEIT)",
    },
}


_MT_RE = re.compile(r"(^MT|MTDE|MTSE|MTILOE|PSEC|MTCSE|MTCS|MT-)", re.I)
_VSEC_RE = re.compile(r"(VSEC|FY-PP|FY-WD|FY-PPS|FY-AIMA)", re.I)
_IFC_RE = re.compile(r"(IFC|D2DA|EnTC_DA|MnE_DA|EE_FOS|IE_FML|IOC-)", re.I)


def subject_area(short_name: str, full_name: str) -> str:
    """Return the UniTime subject-area abbreviation for a Taasika subject."""
    text = f"{short_name or ''} {full_name or ''}"
    if _IFC_RE.search(text):
        return "IFC"
    if _VSEC_RE.search(text):
        return "VSEC"
    if _MT_RE.search(text) or "M Tech" in (full_name or "") or "M.Tech" in (full_name or ""):
        return "MT"
    return "CS"


def department_code(dept_id: Optional[int]) -> str:
    if dept_id is None:
        return "0101"
    return DEPARTMENT_CODES.get(dept_id, "0101")


_YEAR_FROM_SHORT = [
    (re.compile(r"^FY", re.I), ("FY", "First Year B.Tech.")),
    (re.compile(r"^SY", re.I), ("SY", "Second Year B.Tech.")),
    (re.compile(r"^TY", re.I), ("TY", "Third Year B.Tech.")),
    (re.compile(r"^BT", re.I), ("BT", "Final Year B.Tech.")),
    (re.compile(r"^MT", re.I), ("MT", "M.Tech.")),
]


def year_classification(short_name: str, semester: int) -> tuple[str, str]:
    """Return (code, name) for an academic classification."""
    for pattern, value in _YEAR_FROM_SHORT:
        if pattern.match(short_name or ""):
            return value
    sem = semester or 0
    if sem in (1, 2):
        return ("FY", "First Year B.Tech.")
    if sem in (3, 4):
        return ("SY", "Second Year B.Tech.")
    if sem in (5, 6):
        return ("TY", "Third Year B.Tech.")
    if sem in (7, 8):
        return ("BT", "Final Year B.Tech.")
    if sem in (9, 10):
        return ("MT", "M.Tech.")
    return ("FY", "First Year B.Tech.")


_MAJOR_PATTERNS = [
    (re.compile(r"\bMDM\b"), ("MDM", "Multi-Disciplinary Minor")),
    (re.compile(r"\bMinor\b", re.I), ("MIN", "Minor of CSE")),
    (re.compile(r"\bReserved\b", re.I), ("RES", "Reserved Cohort")),
    (re.compile(r"(AIMA|AI For Interdisci|AI for Interrdisci)", re.I), ("AIMA", "AI for Interdisciplinary Applications")),
    (re.compile(r"AIML", re.I), ("AIML", "AI and Machine Learning")),
    (re.compile(r"\bPython Programming\b", re.I), ("PP", "Python Programming")),
    (re.compile(r"\bWeb Design\b", re.I), ("WD", "Web Design")),
    (re.compile(r"\bProgramming for Prob(\.|lem)? ?Solving\b", re.I), ("PPS", "Programming for Problem Solving")),
    (re.compile(r"(Artificial Intelligence|MT-?AI\b)", re.I), ("AI", "Artificial Intelligence")),
    (re.compile(r"(Data Sci\w*|MT-?DS\b)", re.I), ("DS", "Data Science")),
    (re.compile(r"\b(Information Security|MT-CSIS|CSIS)\b"), ("IS", "Information Security")),
    (re.compile(r"\bOpen Elective\b", re.I), ("OE", "Open Elective Track")),
    (re.compile(r"\b(Information Technology|MT-IT|FY-IT)\b"), ("IT", "Information Technology")),
    (re.compile(r"\b(Computer Engineering|CSE|Comp\.? Engg\.?|Comp\.? Engineering)\b", re.I), ("CE", "Computer Engineering")),
]


def major_for_class(short_name: str, full_name: str) -> tuple[str, str]:
    """Return (code, name) for the posMajor of a Taasika class."""
    text = f"{short_name or ''} {full_name or ''}"
    for pattern, value in _MAJOR_PATTERNS:
        if pattern.search(text):
            return value
    return ("CE", "Computer Engineering")


_PAIR_SUFFIX_RE = re.compile(r"(\s*-?\s*Lab(oratory)?|\s+Lab(oratory)?|\s*-?\s*Tut(orial)?|\s+Tut(orial)?)\s*$", re.I)


def _strip_pair_suffix(short_name: str) -> str:
    return _PAIR_SUFFIX_RE.sub("", short_name or "").strip()


def find_course_pairs(subjects: list[dict]) -> dict:
    """Identify Lec+Lab/Tut subject pairs sharing the same base shortName.

    Returns a dict with:
      * ``pair_of``    : subjectId -> partner subjectId (lec <-> lab)
      * ``lec_to_lab`` : lec_subjectId -> lab_subjectId
      * ``lab_to_lec`` : lab_subjectId -> lec_subjectId
      * ``primary_of`` : subjectId -> the subjectId that owns the merged course
                         (always the Lec member of the pair, or the subject
                         itself when unpaired)
    """
    by_short = {s["subjectShortName"]: s for s in subjects}
    pair_of: dict[int, int] = {}
    lec_to_lab: dict[int, int] = {}
    lab_to_lec: dict[int, int] = {}
    primary_of: dict[int, int] = {}

    for s in subjects:
        sid = s["subjectId"]
        sn = s["subjectShortName"] or ""
        is_companion = bool(s.get("batches")) or "lab" in sn.lower() or "tut" in sn.lower()
        if not is_companion:
            continue
        base = _strip_pair_suffix(sn)
        if base == sn or not base:
            continue
        match = by_short.get(base)
        if not match:
            continue
        if bool(match.get("batches")):
            continue
        lec_id = match["subjectId"]
        pair_of[sid] = lec_id
        pair_of[lec_id] = sid
        lec_to_lab[lec_id] = sid
        lab_to_lec[sid] = lec_id
        primary_of[sid] = lec_id
        primary_of[lec_id] = lec_id

    for s in subjects:
        primary_of.setdefault(s["subjectId"], s["subjectId"])

    return {
        "pair_of": pair_of,
        "lec_to_lab": lec_to_lab,
        "lab_to_lec": lab_to_lec,
        "primary_of": primary_of,
    }


def combined_credits(lec: dict | None, lab: dict | None) -> float:
    """Indian-style credit formula: 1 cr per lec hour + 0.5 cr per lab hour."""
    cr = 0.0
    if lec:
        cr += (lec.get("eachSlot") or 0) * (lec.get("nSlots") or 0)
    if lab:
        cr += 0.5 * (lab.get("eachSlot") or 0) * (lab.get("nSlots") or 0)
    return max(1.0, round(cr, 1))


def clean_course_title(name: str) -> str:
    """Strip trailing Lab/Tut markers from a subject name to use as course title."""
    text = (name or "").strip()
    for suffix in (
        " Laboratory",
        " Lab",
        " Tutorial",
        " Tut",
        " - Laboratory",
        " - Lab",
        " - Tut",
        "-Laboratory",
        "-Lab",
    ):
        if text.lower().endswith(suffix.lower()):
            text = text[: -len(suffix)].strip()
    return text
