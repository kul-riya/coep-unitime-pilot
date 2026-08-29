"""Generate buildingRoomImport.xml, roomSharing.xml, and travelTimes.xml."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from taasika_loader import load
from xml_common import LICENSE_HEADER, xml_escape


CAMPUS = "COEP"
TERM = "Spr"
YEAR = 2026
OUT_DIR = Path(__file__).resolve().parent.parent / "unitime-out"


BUILDINGS: Dict[str, Dict[str, object]] = {
    "AC": {
        "name": "Academic Complex",
        "abbreviation": "AC",
        "x": 100,
        "y": 100,
    },
    "ENTCX": {
        "name": "ENTC Extension Building",
        "abbreviation": "ENTCX",
        "x": 200,
        "y": 100,
    },
    "CSED": {
        "name": "Computer Engineering and IT Department",
        "abbreviation": "CSED",
        "x": 150,
        "y": 150,
    },
    "NCSE": {
        "name": "New CSE Building",
        "abbreviation": "NCSE",
        "x": 175,
        "y": 175,
    },
    "BHAU": {
        "name": "Bhau Institute",
        "abbreviation": "BHAU",
        "x": 300,
        "y": 200,
    },
    "ONL": {
        "name": "Online (Virtual)",
        "abbreviation": "ONL",
        "x": 0,
        "y": 0,
    },
    "UNAV": {
        "name": "Unavailable Lab Pool",
        "abbreviation": "UNAV",
        "x": 250,
        "y": 250,
    },
}


def _building_for(room_name: str, room_short: str) -> str:
    name = (room_name or "").lower()
    short = (room_short or "").lower()
    if "academic complex" in name or "acadmie" in name or "acadmic" in name:
        return "AC"
    if "new cse building" in name:
        return "NCSE"
    if "bhau" in name:
        return "BHAU"
    if "online" in name:
        return "ONL"
    if "lab-unavailable" in name or "unavail" in short:
        return "UNAV"
    if "entc ext" in name or short.startswith("cet") or "sh entc" in name or short == "sh":
        return "ENTCX"
    return "CSED"


def _room_classification(room_name: str, room_short: str) -> str:
    text = f"{room_name or ''} {room_short or ''}".lower()
    if "lab" in text and "lecture hall" not in text and "online" not in text:
        return "lab"
    if "online" in text:
        return "virtual"
    return "classroom"


def _scheduled_room_type(room_name: str, room_short: str) -> str:
    cls = _room_classification(room_name, room_short)
    if cls == "lab":
        return "computingLab"
    if cls == "virtual":
        return "genClassroom"
    return "genClassroom"


def _room_number(room_short: str, room_name: str, building: str) -> str:
    short = (room_short or "").strip()
    short_clean = re.sub(r"[()\s]+", "", short)
    short_clean = short_clean.strip("_-")
    return short_clean or re.sub(r"[^A-Za-z0-9]+", "", room_name or "x")[:16]


def _wrap(root_attrs: str, body: str) -> str:
    return LICENSE_HEADER + f"{root_attrs}\n{body}"


def _gen_buildings(rooms: List[dict], term: str = TERM) -> None:
    by_building: Dict[str, List[dict]] = defaultdict(list)
    for r in rooms:
        b = _building_for(r["roomName"], r["roomShortName"])
        by_building[b].append(r)

    lines: List[str] = [
        f'<buildingsRooms campus="{CAMPUS}" term="{term}" year="{YEAR}">'
    ]
    for code, rooms_in in by_building.items():
        meta = BUILDINGS[code]
        lines.append(
            f'  <building externalId="taasika-bldg-{code}" '
            f'abbreviation="{meta["abbreviation"]}" '
            f'locationX="{meta["x"]}" locationY="{meta["y"]}" '
            f'name="{xml_escape(meta["name"])}">'
        )
        seen_room_numbers: set[str] = set()
        for r in rooms_in:
            cls = _room_classification(r["roomName"], r["roomShortName"])
            schedt = _scheduled_room_type(r["roomName"], r["roomShortName"])
            instr = "True" if cls != "virtual" else "False"
            room_nbr = _room_number(r["roomShortName"], r["roomName"], code)
            if room_nbr in seen_room_numbers:
                continue
            seen_room_numbers.add(room_nbr)
            lines.append(
                f'    <room externalId="taasika-room-{r["roomId"]}" '
                f'locationX="{meta["x"]}" locationY="{meta["y"]}" '
                f'roomNumber="{xml_escape(room_nbr)}" '
                f'displayName="{xml_escape(r["roomShortName"])}" '
                f'roomClassification="{cls}" '
                f'capacity="{r["roomCount"] or 0}" '
                f'instructional="{instr}" '
                f'scheduledRoomType="{schedt}">'
            )
            lines.append('      <roomDepartments>')
            lines.append('        <assigned departmentNumber="0101" percent="100"/>')
            lines.append('      </roomDepartments>')
            features: List[Tuple[str, str]] = []
            if cls == "lab":
                features.append(("computerProjection", "Computer Projection"))
                features.append(("puccComputer", "Computer"))
            if cls == "classroom":
                features.append(("computerProjection", "Computer Projection"))
            if features:
                lines.append('      <roomFeatures>')
                for feature, value in features:
                    lines.append(
                        f'        <roomFeature feature="{feature}" value="{xml_escape(value)}"/>'
                    )
                lines.append('      </roomFeatures>')
            lines.append('    </room>')
        lines.append('  </building>')
    lines.append('</buildingsRooms>\n')
    (OUT_DIR / "7buildingRoomImport.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def _gen_room_sharing(rooms: List[dict], fixed_entries: List[dict], term: str = TERM) -> None:
    """Mark weekends (08:30 - 18:30) as unavailable on every room."""
    lines: List[str] = [
        f'<roomSharing campus="{CAMPUS}" year="{YEAR}" term="{term}" '
        f'created="Generated from Taasika snapshot 240" timeFormat="HHmm">'
    ]
    seen_sharing: set[str] = set()
    for r in rooms:
        room_nbr = _room_number(r["roomShortName"], r["roomName"], "")
        building = _building_for(r["roomName"], r["roomShortName"])
        key = f"{building}-{room_nbr}"
        if key in seen_sharing:
            continue
        seen_sharing.add(key)
        lines.append(
            f'  <location id="taasika-room-{r["roomId"]}" '
            f'building="{building}" roomNbr="{xml_escape(room_nbr)}">'
        )
        lines.append('    <department code="0101" control="true"/>')
        lines.append('    <sharing>')
        lines.append('      <unavailable days="SSu" start="0830" end="1830"/>')
        lines.append('    </sharing>')
        lines.append('  </location>')
    lines.append('</roomSharing>\n')
    (OUT_DIR / "8roomSharing.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def _gen_travel_times(rooms: List[dict], term: str = TERM) -> None:
    by_building: Dict[str, List[dict]] = defaultdict(list)
    for r in rooms:
        by_building[_building_for(r["roomName"], r["roomShortName"])].append(r)

    lines: List[str] = [
        f'<traveltimes campus="{CAMPUS}" year="{YEAR}" term="{term}" '
        f'created="Generated from Taasika snapshot 240">'
    ]
    buildings_used = list(by_building.keys())
    for src in buildings_used:
        for r_src in by_building[src][:1]:
            src_nbr = _room_number(r_src["roomShortName"], r_src["roomName"], src)
            lines.append(f'  <from building="{src}" roomNbr="{xml_escape(src_nbr)}">')
            for dst in buildings_used:
                if dst == src:
                    continue
                for r_dst in by_building[dst][:1]:
                    dst_nbr = _room_number(r_dst["roomShortName"], r_dst["roomName"], dst)
                    minutes = 5 if {src, dst} != {"CSED", "NCSE"} else 3
                    lines.append(
                        f'    <to building="{dst}" roomNbr="{xml_escape(dst_nbr)}">{minutes}</to>'
                    )
            lines.append('  </from>')
    lines.append('</traveltimes>\n')
    (OUT_DIR / "9travelTimes.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def main(term: str = TERM) -> None:
    data = load(snapshot_id=240, tables=["room", "fixedEntry"])
    rooms = sorted(data.filtered("room"), key=lambda r: r["roomId"])
    fes = data.filtered("fixedEntry")

    _gen_buildings(rooms, term=term)
    _gen_room_sharing(rooms, fes, term=term)
    _gen_travel_times(rooms, term=term)

    for name in ("7buildingRoomImport.xml", "8roomSharing.xml", "9travelTimes.xml"):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate 7buildingRoomImport.xml through 9travelTimes.xml")
    parser.add_argument("--term", default=TERM, help="UniTime academic term (default: %(default)s)")
    args = parser.parse_args()
    main(term=args.term)
