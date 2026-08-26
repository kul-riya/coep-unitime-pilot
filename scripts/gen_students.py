"""Generate studentInfo / studentRequest / studentenrollments for the
preference-based simulation.

Student externalId: ``61yy03aaa``
  yy  = 01 FY, 02 SY, 03 TY, 04 BT, 05 MT
  03  = branch marker (fixed)
  aaa = 001..N within a B.Tech year (CSE first, then AIML);
        MT uses 001..N across programs.

Intake (confirmed): CSE FY=160, CSE SY/TY/BT=200 (2 divisions of 100;
DSY join in SY). AIML = 100 extra per year. M.Tech unchanged.
CSE/AIML students are not enrolled in MDM or OE (other-dept room blocks)
or in BT Minor (BT takes DE4 instead).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from classifications import companion_itype
from intake import N_AIML, N_CSE, N_DIVISIONS, year_headcount
from xml_common import LICENSE_HEADER, xml_escape


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"
SCRIPTS_DIR = Path(__file__).resolve().parent

GIVEN_NAMES = [
    "Aarav", "Aanya", "Aditya", "Ananya", "Arjun", "Bhavika", "Chirag", "Diya",
    "Dev", "Esha", "Farhan", "Gauri", "Harsh", "Ishita", "Jai", "Kavya",
    "Lakshay", "Meera", "Neel", "Omkar", "Priya", "Rahul", "Riya", "Sahil",
    "Tara", "Uday", "Varun", "Yash", "Zara", "Aditi",
]
LAST_NAMES = [
    "Patil", "Sharma", "Kulkarni", "Joshi", "Deshpande", "Iyer", "Nair",
    "Verma", "Gupta", "Singh", "Rao", "Reddy", "Khan", "Mehta", "Shah",
]

# yy codes in student id 61yy03aaa
YEAR_YY = {"FY": "01", "SY": "02", "TY": "03", "BT": "04", "MT": "05"}


def fy_cse_division(seq: int) -> int:
    """0-based CSE lecture index for FY seq 1..160 across 4 FY-CSE cohorts."""
    n_cse = N_CSE["FY"]
    return min((seq - 1) * 4 // max(n_cse, 1), 3)


def sy_ty_bt_division(seq: int, n_cse: int) -> int:
    """0 = Div1, 1 = Div2. CSE 100+100; AIML 50+50 into the same two lectures."""
    if seq <= n_cse:
        return 0 if seq <= n_cse // N_DIVISIONS else 1
    aiml_seq = seq - n_cse
    return 0 if aiml_seq <= N_AIML // N_DIVISIONS else 1


def section_index_for_division(div: int, n_sections: int, n_divisions: int) -> int:
    """Map cohort division to a 0-based section index (stable, equal split)."""
    if n_sections <= 0:
        return 0
    if n_sections >= n_divisions:
        return min(div, n_sections - 1)
    return min(div * n_sections // n_divisions, n_sections - 1)


def student_id(year_key: str, seq: int) -> str:
    return f"61{YEAR_YY[year_key]}03{seq:03d}"


def student_name(seq: int) -> tuple[str, str]:
    first = GIVEN_NAMES[(seq - 1) % len(GIVEN_NAMES)]
    last = LAST_NAMES[((seq - 1) // len(GIVEN_NAMES)) % len(LAST_NAMES)]
    return first, last


def equal_pick(seq: int, n_options: int) -> int:
    """0-based option index for 1-based seq, as equal as possible."""
    if n_options <= 0:
        return 0
    return (seq - 1) % n_options


# ---------------------------------------------------------------------------
# Curriculum: shortNames from subject_index / course type report.
# MDM and OE are other-department room blocks — not in this curriculum.
# BT takes one DE4 (equal split); no minor.
# ---------------------------------------------------------------------------

CURRICULUM: dict[str, dict] = {
    "FY": {
        "default": [
            "AIMA",
            "DS(FY)",
            "DS(FY)-Tut",
            "PP(FY)",
            "PP(FY)-Lab",
            "PPS(FY)",
            "PPS(FY)-Lab",
            "WD(FY)",
            "WD(FY)-Lab",
            "FY-Reserved",
        ],
        "electives": {},
    },
    "SY": {
        "default": [
            "CO",
            "CoI",
            "DTL-Lab",
            "Eco",
            "OOPD",
            "OOPD-Lab",
            "TOC",
            "TOC-Tut",
        ],
        "electives": {},
    },
    "TY": {
        "default": [
            "AI",
            "AI-Lab",
            "CN",
            "CN-Lab",
            "DAA",
            "DAA-Lab",
        ],
        "electives": {
            "DE": [
                ["DE2-ASP", "DE2-ASP-Lab"],
                ["DE2-BCT", "DE2-BCT-Lab"],
                ["DE2-DSci", "DE2-DSci-Lab"],
            ],
        },
    },
    "BT": {
        "default": [],
        "electives": {
            "DE": [
                ["DE4-GIS", "DE4-GIS-Lab"],
                ["DE4-GPU", "DE4-GPU-Lab"],
                ["DE4-IBCS", "DE4-IBC-Lab"],
            ],
        },
    },
}

# M.Tech programs: (label, count, default shorts, psec option shorts)
MT_PROGRAMS: list[tuple[str, int, list[str], list[str]]] = [
    (
        "CE",
        20,
        ["DMML", "DMML-Lab", "SIC", "SIC-Lab", "ES", "ES-Lab", "MT-ETCSA", "MT-ETCSALab"],
        ["PSEC2-CCV", "PSEC2-NLP", "PSEC3-DL", "PSEC3-MT", "PSEC2-BT"],
    ),
    (
        "CSIS",
        25,
        ["MT-NS", "MT-NS-Lab", "MT-WNS", "MT-WNS-Lab", "MT-DFDR", "MT-DFDR-Lab"],
        ["PSEC2-CCS", "PSEC3-WS", "PSEC3-ITS", "PSEC2-BT"],
    ),
    (
        "AI",
        25,
        ["MT-DL", "MTDL-Lab", "MT-GAN", "MT-GAN-Lab", "MT-OT", "MT-OT-Lab"],
        ["PSEC2-EAI", "PSEC2-MLPS", "PSEC3-GNN", "MT-NLP"],
    ),
    (
        "DS",
        60,
        ["MT-BDAAS", "MT-BDAAS-Lab", "MT-AMLD", "MT-AMLD-Lab", "MT-MLOS", "MT-MLOS-Lab"],
        ["PSEC2-CV", "PSEC2-MTRP", "PSEC3-GAN", "PSEC2-EAI"],
    ),
]


def load_indexes() -> tuple[dict, dict[str, tuple[int, dict]], dict[int, list[int]], dict[int, list[int]], dict[int, str], dict[tuple[str, str, str, int], int]]:
    subject_idx = json.loads((SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8"))
    offering = json.loads((SCRIPTS_DIR / "offering_index.json").read_text(encoding="utf-8"))
    by_short: dict[str, tuple[int, dict]] = {}
    for sid, info in subject_idx.items():
        by_short[info["shortName"]] = (int(sid), info)

    lec_suf: dict[int, list[int]] = defaultdict(list)
    lab_suf: dict[int, list[int]] = defaultdict(list)
    companion_type: dict[int, str] = {}
    for key, suf in offering["section_offsets"].items():
        sid_s, rest = key.split("|", 1)
        sid = int(sid_s)
        if rest.startswith("Lec"):
            lec_suf[sid].append(int(suf))
        else:
            lab_suf[sid].append(int(suf))
            kind = rest.split("-", 1)[0]
            companion_type.setdefault(sid, kind if kind in ("Lab", "Tut", "Rec") else "Lab")
    for d in (lec_suf, lab_suf):
        for sid in d:
            d[sid] = sorted(set(d[sid]))

    class_limits: dict[tuple[str, str, str, int], int] = {}
    for raw, lim in (offering.get("class_limits") or {}).items():
        parts = str(raw).split("|")
        if len(parts) != 4:
            continue
        area, nbr, typ, suf = parts
        class_limits[(area, nbr, typ, int(suf))] = int(lim)
    return subject_idx, by_short, lec_suf, lab_suf, companion_type, class_limits


def class_tags_for_short(
    short: str,
    by_short: dict[str, tuple[int, dict]],
    lec_suf: dict[int, list[int]],
    lab_suf: dict[int, list[int]],
    companion_type: dict[int, str],
    rr: int,
    *,
    section_pick: int | None = None,
) -> list[tuple[str, str, str, int]]:
    """Return list of (subjectArea, courseNbr, type, suffix) for one shortName."""
    if short not in by_short:
        return []
    sid, info = by_short[short]
    area = info["subjectArea"]
    nbr = info["courseNumber"]
    tags: list[tuple[str, str, str, int]] = []

    lecs = lec_suf.get(sid) or []
    if lecs and not info.get("isLab"):
        pick = section_pick if section_pick is not None else (rr % len(lecs))
        suf = lecs[pick % len(lecs)]
        tags.append((area, nbr, "Lec", suf))

    labs = lab_suf.get(sid) or []
    itype = companion_type.get(sid) or companion_itype(short)
    if labs:
        pick = section_pick if section_pick is not None else (rr % len(labs))
        suf = labs[pick % len(labs)]
        tags.append((area, nbr, itype, suf))
    elif info.get("isLab"):
        pass

    if not info.get("isLab"):
        for other_sn, (osid, oinfo) in by_short.items():
            if oinfo.get("primarySubjectId") == sid and oinfo.get("isLab"):
                olabs = lab_suf.get(osid) or []
                if olabs and other_sn not in (short,):
                    if oinfo["courseNumber"] == nbr and not any(t[2] in ("Lab", "Tut", "Rec") for t in tags):
                        pick = section_pick if section_pick is not None else (rr % len(olabs))
                        suf = olabs[pick % len(olabs)]
                        otype = companion_type.get(osid) or companion_itype(other_sn)
                        tags.append((area, nbr, otype, suf))
                break

    return tags


def enroll_shorts(
    shorts: Iterable[str],
    by_short: dict,
    lec_suf: dict,
    lab_suf: dict,
    companion_type: dict[int, str],
    rr: int,
    *,
    year_key: str | None = None,
    seq: int | None = None,
) -> list[tuple[str, str, str, int]]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[tuple[str, str, str, int]] = []
    shorts_list = list(shorts)
    explicit_labs = {s for s in shorts_list if s in by_short and by_short[s][1].get("isLab")}

    def section_pick_for(short: str) -> int | None:
        if year_key is None or seq is None or short not in by_short:
            return None
        sid, info = by_short[short]
        lecs = lec_suf.get(sid) or []
        labs = lab_suf.get(sid) or []
        n = len(labs) if info.get("isLab") else (len(lecs) or len(labs) or 1)
        n_cse = N_CSE.get(year_key or "", 0)
        if year_key == "FY":
            is_aiml = seq > n_cse
            if is_aiml:
                return n - 1 if n >= 5 else (seq - 1) % n
            if n >= 4:
                return fy_cse_division(seq)
            return (seq - 1) % n
        if year_key in ("SY", "TY", "BT"):
            div = sy_ty_bt_division(seq, n_cse)
            if n <= 2 and lecs and not info.get("isLab"):
                return div
            return section_index_for_division(div, n, N_DIVISIONS)
        return None

    for short in shorts_list:
        if short not in by_short:
            continue
        sid, info = by_short[short]
        pick = section_pick_for(short)
        tags = class_tags_for_short(
            short, by_short, lec_suf, lab_suf, companion_type, rr, section_pick=pick
        )
        if not info.get("isLab") and explicit_labs:
            tags = [t for t in tags if t[2] not in ("Lab", "Tut", "Rec")]
        for t in tags:
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def assign_within_limits(
    tags: list[tuple[str, str, str, int]],
    class_fill: dict[tuple[str, str, str, int], int],
    class_limits: dict[tuple[str, str, str, int], int],
    overflow: dict[str, int],
) -> list[tuple[str, str, str, int]]:
    """Place each enrollment into a section that still has seat capacity."""
    assigned: list[tuple[str, str, str, int]] = []
    by_course_type: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for (area, nbr, typ, suf), _lim in class_limits.items():
        by_course_type[(area, nbr, typ)].append(suf)
    for key in by_course_type:
        by_course_type[key] = sorted(set(by_course_type[key]))

    for area, nbr, typ, suf in tags:
        preferred = (area, nbr, typ, suf)
        candidates = [preferred]
        for alt in by_course_type.get((area, nbr, typ), []):
            cand = (area, nbr, typ, alt)
            if cand not in candidates:
                candidates.append(cand)
        placed = False
        for cand in candidates:
            limit = class_limits.get(cand)
            if limit is None:
                class_fill[cand] += 1
                assigned.append(cand)
                placed = True
                break
            if class_fill[cand] < limit:
                class_fill[cand] += 1
                assigned.append(cand)
                placed = True
                break
        if not placed:
            overflow[f"{area} {nbr} {typ}"] += 1
    return assigned


def main() -> None:
    subject_idx, by_short, lec_suf, lab_suf, companion_type, class_limits = load_indexes()

    def resolve_btech(year_key: str, seq: int) -> list[str]:
        cfg = CURRICULUM[year_key]
        shorts: list[str] = list(cfg["default"])
        for group, options in cfg["electives"].items():
            idx = equal_pick(seq, len(options))
            choice = options[idx]
            if choice is None:
                continue
                if isinstance(choice, list):
                    shorts.extend(choice)
                else:
                    shorts.append(choice)
        # dedupe preserving order
        seen: set[str] = set()
        out: list[str] = []
        for s in shorts:
            if s.lower().startswith("honor"):
                continue
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    # incremental=true: only create/update students in this file (safer re-import).
    # Omit studentGroups here: UniTime StudentImport merge()s groups before flush and
    # can throw TransientObjectException on large cohorts (see StudentImport.java).
    info_lines = [
        LICENSE_HEADER,
        f'<students campus="{CAMPUS}" year="{YEAR}" term="{TERM}" incremental="true">',
    ]
    req_lines = [
        LICENSE_HEADER,
        f'<request campus="{CAMPUS}" year="{YEAR}" term="{TERM}" incremental="true">',
    ]
    enr_lines = [
        LICENSE_HEADER,
        f'<studentEnrollments campus="{CAMPUS}" year="{YEAR}" term="{TERM}">',
    ]

    stats: dict[str, int] = defaultdict(int)
    missing_shorts: set[str] = set()
    overflow: dict[str, int] = defaultdict(int)
    class_fill: dict[tuple[str, str, str, int], int] = defaultdict(int)
    total = 0

    def emit_student(
        ext_id: str,
        seq_for_name: int,
        area: str,
        class_code: str,
        major: str,
        group: str,
        shorts: list[str],
        rr: int,
        year_key: str | None = None,
    ) -> None:
        nonlocal total
        total += 1
        first, last = student_name(seq_for_name)
        email = f"{ext_id.lower()}@students.unitime.local"

        info_lines.append(
            f'  <student externalId="{xml_escape(ext_id)}" '
            f'firstName="{xml_escape(first)}" lastName="{xml_escape(last)}" '
            f'email="{xml_escape(email)}">'
        )
        info_lines.append("    <studentAcadAreaClass>")
        info_lines.append(
            f'      <acadAreaClass academicArea="{area}" academicClass="{class_code}"/>'
        )
        info_lines.append("    </studentAcadAreaClass>")
        info_lines.append("    <studentMajors>")
        info_lines.append(
            f'      <major academicArea="{area}" academicClass="{class_code}" code="{major}"/>'
        )
        info_lines.append("    </studentMajors>")
        # group kept for logging only; not written to XML (see header comment)
        _ = group
        info_lines.append("  </student>")

        tags = enroll_shorts(
            shorts,
            by_short,
            lec_suf,
            lab_suf,
            companion_type,
            rr,
            year_key=year_key or class_code,
            seq=seq_for_name,
        )
        tags = assign_within_limits(tags, class_fill, class_limits, overflow)
        for s in shorts:
            if s not in by_short:
                missing_shorts.add(s)

        # course requests = unique offerings
        req_lines.append(f'  <student key="{xml_escape(ext_id)}">')
        req_lines.append('    <updateCourseRequests commit="true">')
        seen_courses: set[tuple[str, str]] = set()
        for area_a, nbr, _typ, _suf in tags:
            if (area_a, nbr) in seen_courses:
                continue
            seen_courses.add((area_a, nbr))
            req_lines.append(
                f'      <courseOffering subjectArea="{xml_escape(area_a)}" '
                f'courseNumber="{xml_escape(nbr)}"/>'
            )
        req_lines.append("    </updateCourseRequests>")
        req_lines.append("  </student>")

        enr_lines.append(f'  <student externalId="{xml_escape(ext_id)}">')
        for area_a, nbr, typ, suf in tags:
            enr_lines.append(
                f'    <class subject="{xml_escape(area_a)}" '
                f'courseNbr="{xml_escape(nbr)}" type="{typ}" suffix="{suf}"/>'
            )
            stats[f"{area_a} {nbr} {typ} {suf}"] += 1
        enr_lines.append("  </student>")

    # ---- B.Tech years ----
    for year_key in ("FY", "SY", "TY", "BT"):
        n_cse = N_CSE[year_key]
        n_year = year_headcount(year_key)
        for seq in range(1, n_year + 1):
            major = "CE" if seq <= n_cse else "AIML"
            group = f"{year_key}-{major}"
            ext = student_id(year_key, seq)
            shorts = resolve_btech(year_key, seq)
            emit_student(
                ext_id=ext,
                seq_for_name=seq,
                area="BT",
                class_code=year_key,
                major=major,
                group=group,
                shorts=shorts,
                rr=seq - 1,
                year_key=year_key,
            )

    # ---- M.Tech ----
    mt_seq = 0
    for prog, count, defaults, psecs in MT_PROGRAMS:
        for i in range(count):
            mt_seq += 1
            ext = student_id("MT", mt_seq)
            psec = psecs[equal_pick(i + 1, len(psecs))] if psecs else None
            shorts = list(defaults)
            if psec:
                shorts.append(psec)
            # optional OE-DS for some fraction? keep program defaults only + one PSEC
            emit_student(
                ext_id=ext,
                seq_for_name=mt_seq,
                area="MT",
                class_code="MT",
                major={"CE": "CE", "CSIS": "IS", "AI": "AI", "DS": "DS"}[prog],
                group=f"MT-{prog}",
                shorts=shorts,
                rr=i,
            )

    info_lines.append("</students>\n")
    req_lines.append("</request>\n")
    enr_lines.append("</studentEnrollments>\n")

    (OUT_DIR / "studentInfo.xml").write_text("\n".join(info_lines), encoding="utf-8")
    (OUT_DIR / "studentRequest.xml").write_text("\n".join(req_lines), encoding="utf-8")
    (OUT_DIR / "studentenrollments.xml").write_text("\n".join(enr_lines), encoding="utf-8")
    (OUT_DIR / "14studentInfo.xml").write_text("\n".join(info_lines), encoding="utf-8")
    (OUT_DIR / "15studentRequest.xml").write_text("\n".join(req_lines), encoding="utf-8")
    (OUT_DIR / "16studentenrollments.xml").write_text("\n".join(enr_lines), encoding="utf-8")

    summary = {
        "total_students": total,
        "btech_by_year": {y: year_headcount(y) for y in ("FY", "SY", "TY", "BT")},
        "cse_by_year": dict(N_CSE),
        "aiml_per_year": N_AIML,
        "mt_students": mt_seq,
        "missing_shorts": sorted(missing_shorts),
        "id_format": "61yy03aaa (yy=01FY..05MT)",
        "overflow_unplaced": dict(overflow),
        "note": (
            "CSE FY=160; CSE SY/TY/BT=200 (2 divisions of 100, DSY join in SY). "
            "AIML=100 extra per year on the same basket. "
            "MDM/OE are other-dept room blocks (no enrollments). "
            "BT has no minor; every BT student takes one DE4."
        ),
    }
    (OUT_DIR.parent / "solutions" / "enrollment_sim_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    for name in ("studentInfo.xml", "studentRequest.xml", "studentenrollments.xml"):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")
    print(f"total students: {total} (B.Tech {sum(year_headcount(y) for y in ('FY','SY','TY','BT'))} + MT {mt_seq})")
    if overflow:
        print("WARNING students not placed (class at limit):")
        for k, n in sorted(overflow.items(), key=lambda kv: -kv[1])[:20]:
            print(f"  {k}: {n}")
    if missing_shorts:
        print("WARNING missing shortNames:", ", ".join(sorted(missing_shorts)))

    # Quick elective distribution checks
    for year_key in ("SY", "TY", "BT"):
        n_year = year_headcount(year_key)
        for group, options in CURRICULUM[year_key]["electives"].items():
            counts = [0] * len(options)
            for seq in range(1, n_year + 1):
                counts[equal_pick(seq, len(options))] += 1
            print(f"  {year_key} {group}: {counts}")


if __name__ == "__main__":
    main()
