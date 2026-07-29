"""Generate studentInfo / studentRequest / studentenrollments for the
preference-based simulation (no divisions).

Student externalId: ``61yy03aaa``
  yy  = 01 FY, 02 SY, 03 TY, 04 BT, 05 MT
  03  = branch marker (fixed)
  aaa = 001..500 within a B.Tech year (001-400 CSE, 401-500 AIML);
        MT uses 001..N across programs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

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

N_PER_BTECH_YEAR = 500
N_CSE = 400
N_AIML = 100
N_OE_MDM_OPTIONS = 5  # 1 CSE (if any) + other-dept placeholders


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
# OE/MDM lists may include None = other-department (no UniTime enrollment here).
# DE / HONOR / MINOR / DEFAULT use real short names; labs listed when separate
# offerings (DE lec+lab often not merged in courseOffering).
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
        "electives": {
            "OE": ["OE-FOS", None, None, None, None],
            "MDM": ["MDM-DSFA", None, None, None, None],
        },
    },
    "TY": {
        "default": [
            "AI",  # AI-Lab has no sections in snap 240 offering
            "CN",
            "CN-Lab",
            "DAA",
            "DAA-Lab",
        ],
        "electives": {
            # each DE option = list of shortNames to enroll (lec offering + lab offering)
            "DE": [
                ["DE2-ASP", "DE2-ASP-Lab"],
                ["DE2-BCT", "DE2-BCT-Lab"],
                ["DE2-DSci", "DE2-DSci-Lab"],
            ],
            "OE": [None, None, None, None, None],
            "MDM": ["MDM-FDMS", None, None, None, None],  # MDM-FDMSLab via primary
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
            "OE": [None, None, None, None, None],
            "MDM": [None, None, None, None, None],
            "HONOR": [["Honor4-IOT"], ["Honor4-RL"]],
            "MINOR": [["Minor4-DS"]],
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


def load_indexes() -> tuple[dict, dict[str, tuple[int, dict]], dict[int, list[int]], dict[int, list[int]]]:
    subject_idx = json.loads((SCRIPTS_DIR / "subject_index.json").read_text(encoding="utf-8"))
    offering = json.loads((SCRIPTS_DIR / "offering_index.json").read_text(encoding="utf-8"))
    by_short: dict[str, tuple[int, dict]] = {}
    for sid, info in subject_idx.items():
        by_short[info["shortName"]] = (int(sid), info)

    lec_suf: dict[int, list[int]] = defaultdict(list)
    lab_suf: dict[int, list[int]] = defaultdict(list)
    for key, suf in offering["section_offsets"].items():
        sid_s, rest = key.split("|", 1)
        sid = int(sid_s)
        if rest.startswith("Lec"):
            lec_suf[sid].append(int(suf))
        else:
            lab_suf[sid].append(int(suf))
    for d in (lec_suf, lab_suf):
        for sid in d:
            d[sid] = sorted(set(d[sid]))
    return subject_idx, by_short, lec_suf, lab_suf


def expand_mdm_lab(shorts: list[str] | None, by_short: dict) -> list[str]:
    """If MDM-FDMS chosen, also enroll MDM-FDMSLab when it shares the offering."""
    if not shorts:
        return []
    out = list(shorts)
    if "MDM-FDMS" in out and "MDM-FDMSLab" in by_short and "MDM-FDMSLab" not in out:
        # lab sections live on 32756 but same courseNbr as MDM-FDMS — enroll via short
        out.append("MDM-FDMSLab")
    return out


def class_tags_for_short(
    short: str,
    by_short: dict[str, tuple[int, dict]],
    lec_suf: dict[int, list[int]],
    lab_suf: dict[int, list[int]],
    rr: int,
) -> list[tuple[str, str, str, int]]:
    """Return list of (subjectArea, courseNbr, type, suffix) for one shortName."""
    if short not in by_short:
        return []
    sid, info = by_short[short]
    area = info["subjectArea"]
    nbr = info["courseNumber"]
    tags: list[tuple[str, str, str, int]] = []

    lecs = lec_suf.get(sid) or []
    # Some lab companion rows inherit lec list via primary in probe; only emit Lec
    # when this subject actually has Lec offsets (or is the primary non-lab).
    if lecs and not info.get("isLab"):
        suf = lecs[rr % len(lecs)]
        tags.append((area, nbr, "Lec", suf))

    labs = lab_suf.get(sid) or []
    if labs:
        suf = labs[rr % len(labs)]
        tags.append((area, nbr, "Lab", suf))
    elif info.get("isLab"):
        # lab short with sections stored under its own sid only — already handled
        pass

    # Primary lec with lab partner sharing course number: lab offsets on lab sid
    if not info.get("isLab"):
        # find lab short with same primary
        for other_sn, (osid, oinfo) in by_short.items():
            if oinfo.get("primarySubjectId") == sid and oinfo.get("isLab"):
                olabs = lab_suf.get(osid) or []
                if olabs and other_sn not in (short,):
                    # Only auto-add if caller didn't list lab short separately
                    # and course numbers match (merged offering)
                    if oinfo["courseNumber"] == nbr and not any(t[2] == "Lab" for t in tags):
                        suf = olabs[rr % len(olabs)]
                        tags.append((area, nbr, "Lab", suf))
                break

    return tags


def enroll_shorts(
    shorts: Iterable[str],
    by_short: dict,
    lec_suf: dict,
    lab_suf: dict,
    rr: int,
) -> list[tuple[str, str, str, int]]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[tuple[str, str, str, int]] = []
    shorts_list = list(shorts)
    # When both primary and lab short are listed, prefer explicit; avoid double lab
    explicit_labs = {s for s in shorts_list if s in by_short and by_short[s][1].get("isLab")}
    for short in shorts_list:
        if short not in by_short:
            continue
        sid, info = by_short[short]
        if not info.get("isLab"):
            # lec (+ auto lab only if lab short not also listed)
            tags = class_tags_for_short(short, by_short, lec_suf, lab_suf, rr)
            if explicit_labs:
                tags = [t for t in tags if t[2] != "Lab"]
            for t in tags:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
        else:
            tags = class_tags_for_short(short, by_short, lec_suf, lab_suf, rr)
            for t in tags:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
    return out


def picks_for_student(year_key: str, seq: int) -> list[str]:
    """Resolve all shortNames a B.Tech student should attempt to enroll."""
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
            if group == "MDM":
                shorts = expand_mdm_lab(shorts, {})  # patched below with by_short
    return shorts


def main() -> None:
    subject_idx, by_short, lec_suf, lab_suf = load_indexes()

    # Fix MDM lab expansion with real by_short
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
                if choice == "MDM-FDMS":
                    shorts = expand_mdm_lab(shorts, by_short)
                if choice == "MDM-DSFA":
                    pass
        # dedupe preserving order
        seen: set[str] = set()
        out: list[str] = []
        for s in shorts:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    info_lines = [LICENSE_HEADER, f'<students campus="{CAMPUS}" year="{YEAR}" term="{TERM}">']
    req_lines = [LICENSE_HEADER, f'<request campus="{CAMPUS}" year="{YEAR}" term="{TERM}">']
    enr_lines = [
        LICENSE_HEADER,
        f'<studentEnrollments campus="{CAMPUS}" year="{YEAR}" term="{TERM}">',
    ]

    stats: dict[str, int] = defaultdict(int)
    missing_shorts: set[str] = set()
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
        info_lines.append("    <studentGroups>")
        info_lines.append(f'      <studentGroup group="{xml_escape(group)}"/>')
        info_lines.append("    </studentGroups>")
        info_lines.append("  </student>")

        tags = enroll_shorts(shorts, by_short, lec_suf, lab_suf, rr)
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
        for seq in range(1, N_PER_BTECH_YEAR + 1):
            major = "CE" if seq <= N_CSE else "AIML"
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

    # Ensure year-major groups exist for import
    sg_path = OUT_DIR / "studentGroup.xml"
    sg = sg_path.read_text(encoding="utf-8")
    extra_groups = []
    for y in ("FY", "SY", "TY", "BT"):
        for m in ("CE", "AIML"):
            code = f"{y}-{m}"
            if f'code="{code}"' not in sg:
                extra_groups.append(
                    f'  <studentGroup externalId="sim-{code}" '
                    f'code="{code}" name="{y} {m} cohort (simulated)"/>'
                )
    for prog, *_rest in MT_PROGRAMS:
        code = f"MT-{prog}"
        if f'code="{code}"' not in sg and f'code="MT-{prog}"' not in sg:
            # MT-CE already exists as class short name
            if code == "MT-CE" and 'code="MT-CE"' in sg:
                continue
            if f'code="{code}"' not in sg:
                extra_groups.append(
                    f'  <studentGroup externalId="sim-{code}" '
                    f'code="{code}" name="M.Tech {prog} cohort (simulated)"/>'
                )
    if extra_groups:
        sg = sg.replace("</studentGroups>", "\n".join(extra_groups) + "\n</studentGroups>")
        sg_path.write_text(sg, encoding="utf-8")

    summary = {
        "total_students": total,
        "btech_per_year": N_PER_BTECH_YEAR,
        "mt_students": mt_seq,
        "missing_shorts": sorted(missing_shorts),
        "id_format": "61yy03aaa (yy=01FY..05MT)",
    }
    (OUT_DIR.parent / "solutions" / "enrollment_sim_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    for name in ("studentInfo.xml", "studentRequest.xml", "studentenrollments.xml", "studentGroup.xml"):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")
    print(f"total students: {total} (B.Tech {4 * N_PER_BTECH_YEAR} + MT {mt_seq})")
    if missing_shorts:
        print("WARNING missing shortNames:", ", ".join(sorted(missing_shorts)))

    # Quick elective distribution checks
    for year_key in ("SY", "TY", "BT"):
        for group, options in CURRICULUM[year_key]["electives"].items():
            counts = [0] * len(options)
            for seq in range(1, N_PER_BTECH_YEAR + 1):
                counts[equal_pick(seq, len(options))] += 1
            print(f"  {year_key} {group}: {counts}")


if __name__ == "__main__":
    main()
