"""Generate academicArea.xml, academicClassification.xml, Major.xml,
Minor.xml, and studentGroup.xml from the Taasika snapshot.
"""

from __future__ import annotations

from pathlib import Path

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape
from classifications import major_for_class, year_classification


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"


ACADEMIC_AREAS = [
    ("BT", "Bachelor of Technology"),
    ("MT", "Master of Technology"),
]


def area_for_class(short_name: str) -> str:
    if (short_name or "").upper().startswith("MT"):
        return "MT"
    return "BT"


def _wrap(root: str, body: str) -> str:
    return (
        LICENSE_HEADER
        + f'<{root} campus="{CAMPUS}" term="{TERM}" year="{YEAR}">\n'
        + body
        + f'</{root}>\n'
    )


def _academic_areas() -> None:
    lines: list[str] = []
    for code, name in ACADEMIC_AREAS:
        lines.append(
            f'  <academicArea externalId="taasika-area-{code}" '
            f'abbreviation="{code}" title="{xml_escape(name)}"/>\n'
        )
    (OUT_DIR / "academicArea.xml").write_text(
        _wrap("academicAreas", "".join(lines)), encoding="utf-8"
    )


def _classifications(classes) -> None:
    seen: dict[str, str] = {}
    for c in classes:
        code, name = year_classification(c["classShortName"], c["semester"])
        seen.setdefault(code, name)
    lines: list[str] = []
    for code, name in seen.items():
        lines.append(
            f'  <academicClassification externalId="taasika-class-{code}" '
            f'code="{code}" name="{xml_escape(name)}"/>\n'
        )
    (OUT_DIR / "academicClassification.xml").write_text(
        _wrap("academicClassifications", "".join(lines)), encoding="utf-8"
    )


def _majors(classes) -> None:
    seen: dict[tuple[str, str], str] = {}
    for c in classes:
        area = area_for_class(c["classShortName"])
        code, name = major_for_class(c["classShortName"], c["className"])
        seen.setdefault((area, code), name)
    lines: list[str] = []
    for (area, code), name in seen.items():
        lines.append(
            f'  <posMajor externalId="taasika-maj-{area}-{code}" '
            f'code="{code}" name="{xml_escape(name)}" academicArea="{area}"/>\n'
        )
    (OUT_DIR / "Major.xml").write_text(
        _wrap("posMajors", "".join(lines)), encoding="utf-8"
    )


def _minors() -> None:
    body = "  <!-- No minors used; Minor-of-CSE programs are modelled as posMajors. -->\n"
    (OUT_DIR / "Minor.xml").write_text(
        _wrap("posMinors", body), encoding="utf-8"
    )


def _student_groups(classes, batches) -> None:
    lines: list[str] = []
    for c in classes:
        code = c["classShortName"]
        lines.append(
            f'  <studentGroup externalId="taasika-class-{c["classId"]}" '
            f'code="{xml_escape(code)}" name="{xml_escape(c["className"])}"/>\n'
        )
    for b in batches:
        lines.append(
            f'  <studentGroup externalId="taasika-batch-{b["batchId"]}" '
            f'code="{xml_escape(b["batchName"])}" '
            f'name="{xml_escape(b["batchName"])} (Lab Batch, size {b.get("batchCount")})"/>\n'
        )
    (OUT_DIR / "studentGroup.xml").write_text(
        _wrap("studentGroups", "".join(lines)), encoding="utf-8"
    )


def main() -> None:
    data = load(snapshot_id=240, tables=["class", "batch"])
    classes = sorted(data.filtered("class"), key=lambda r: r["classId"])
    batches = sorted(data.filtered("batch"), key=lambda r: r["batchId"])

    _academic_areas()
    _classifications(classes)
    _majors(classes)
    _minors()
    _student_groups(classes, batches)

    for name in (
        "academicArea.xml",
        "academicClassification.xml",
        "Major.xml",
        "Minor.xml",
        "studentGroup.xml",
    ):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
