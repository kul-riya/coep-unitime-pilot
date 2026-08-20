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

EXCLUDED_ROOM_SHORT_NAMES = {"Cogni-34"}

SUPPLEMENTAL_CSE_LABS: List[dict] = [
    {
        "roomId": f"new-cse-lab-f{floor}-{lab:02d}",
        "roomName": f"New CSE Building, Floor {floor}, CSE Lab {lab:02d}",
        "roomShortName": f"CSE-F{floor}-L{lab:02d}",
            "roomCount": 25,
        "snapshotId": 240,
    }
    for floor in range(1, 4)
    for lab in range(1, 7)
]


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


def _gen_buildings(rooms: List[dict]) -> None:
    by_building: Dict[str, List[dict]] = defaultdict(list)
    for r in rooms:
        if (r.get("roomShortName") or "").strip() in EXCLUDED_ROOM_SHORT_NAMES:
            continue
        b = _building_for(r["roomName"], r["roomShortName"])
        by_building[b].append(r)

    lines: List[str] = [
        f'<buildingsRooms campus="{CAMPUS}" term="{TERM}" year="{YEAR}">'
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
            room_capacity = int(r["roomCount"] or 0)
            if cls == "lab" and room_capacity == 20:
                room_capacity = 25
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
                f'capacity="{room_capacity}" '
                # UniTime's Buildings & Rooms XML schema uses this historical
                # misspelling.  Using "instructional" is silently ignored,
                # leaving imported rooms non-instructional and unusable.
                f'instuctional="{instr}" '
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
    (OUT_DIR / "buildingRoomImport.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def _gen_room_sharing(rooms: List[dict], fixed_entries: List[dict]) -> None:
    """Mark a daily LUNCH window (12:30 - 13:30) as unavailable on every room.

    Taasika's ``fixedEntry`` table marks LUNCH slots per class/room/teacher;
    in UniTime we encode it as a campus-wide room unavailability so the
    solver never schedules a class during lunch.
    """
    lunch_count = sum(1 for f in fixed_entries if (f.get("fixedText") or "").upper() == "LUNCH")

    lines: List[str] = [
        f'<roomSharing campus="{CAMPUS}" year="{YEAR}" term="{TERM}" '
        f'created="Generated from Taasika snapshot 240" timeFormat="HHmm">'
    ]
    lines.append(f'  <!-- LUNCH window derived from {lunch_count} fixedEntry rows -->')
    seen_sharing: set[str] = set()
    for r in rooms:
        if (r.get("roomShortName") or "").strip() in EXCLUDED_ROOM_SHORT_NAMES:
            continue
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
        lines.append('      <unavailable days="MTWThF" start="1230" end="1330"/>')
        lines.append('      <unavailable days="SSu" start="0830" end="1830"/>')
        lines.append('    </sharing>')
        lines.append('  </location>')
    lines.append('</roomSharing>\n')
    (OUT_DIR / "roomSharing.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def _gen_travel_times(rooms: List[dict]) -> None:
    by_building: Dict[str, List[dict]] = defaultdict(list)
    for r in rooms:
        if (r.get("roomShortName") or "").strip() in EXCLUDED_ROOM_SHORT_NAMES:
            continue
        by_building[_building_for(r["roomName"], r["roomShortName"])].append(r)

    lines: List[str] = [
        f'<traveltimes campus="{CAMPUS}" year="{YEAR}" term="{TERM}" '
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
                    # Campus walking time supplied by the user: at most four
                    # minutes between any two different buildings.  UniTime
                    # treats the same room (and unlisted same-building room
                    # transitions) as zero travel time.
                    minutes = 4
                    lines.append(
                        f'    <to building="{dst}" roomNbr="{xml_escape(dst_nbr)}">{minutes}</to>'
                    )
            lines.append('  </from>')
    lines.append('</traveltimes>\n')
    (OUT_DIR / "travelTimes.xml").write_text(
        _wrap("", "\n".join(lines)), encoding="utf-8"
    )


def main() -> None:
    data = load(snapshot_id=240, tables=["room", "fixedEntry"])
    rooms = sorted(data.filtered("room"), key=lambda r: r["roomId"]) + SUPPLEMENTAL_CSE_LABS
    fes = data.filtered("fixedEntry")

    _gen_buildings(rooms)
    _gen_room_sharing(rooms, fes)
    _gen_travel_times(rooms)

    for name in ("buildingRoomImport.xml", "roomSharing.xml", "travelTimes.xml"):
        p = OUT_DIR / name
        print(f"wrote {p.relative_to(OUT_DIR.parent)} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
