"""Parse a Taasika MySQL dump and expose its rows as Python dicts.

Only the INSERT statements for the tables we care about are parsed - DDL,
views, triggers, and comments are ignored. Rows can be filtered by
``snapshot_id`` for the tables that have one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional


SQL_PATH_DEFAULT = (
    Path(__file__).resolve().parent.parent
    / "taasika2-foss-26jan26.sql"
    / "taasika2-foss-26jan26.sql"
)


TABLE_COLUMNS: Dict[str, List[str]] = {
    "batch": ["batchId", "batchName", "batchCount", "snapshotId"],
    "batchCanOverlap": ["boId", "batchId", "batchOverlapId", "snapshotId"],
    "batchClass": ["bcId", "batchId", "classId", "snapshotId"],
    "batchRoom": ["brId", "batchId", "roomId", "snapshotId"],
    "class": ["classId", "className", "classShortName", "semester", "classCount", "snapshotId"],
    "classRoom": ["crId", "classId", "roomId", "snapshotId"],
    "config": ["configId", "configName", "dayBegin", "slotDuration", "nSlots", "deptId", "incharge", "daysInWeek"],
    "dept": ["deptId", "deptName", "deptShortName"],
    "fixedEntry": ["feId", "ttId", "fixedText", "snapshotId"],
    "overlappingSBT": ["osbtId", "sbtId", "sbtOverlapId", "snapshotId"],
    "room": ["roomId", "roomName", "roomShortName", "roomCount", "snapshotId"],
    "snapshot": ["snapshotId", "snapshotName", "snapshotCreator", "createTime", "modifyTime", "configId"],
    "subject": ["subjectId", "subjectName", "subjectShortName", "eachSlot", "nSlots", "batches", "snapshotId"],
    "subjectBatchTeacher": ["sbtId", "subjectId", "batchId", "teacherId", "snapshotId"],
    "subjectClassTeacher": ["sctId", "subjectId", "classId", "teacherId", "snapshotId"],
    "subjectRoom": ["srId", "subjectId", "roomId", "snapshotId"],
    "teacher": ["teacherId", "teacherName", "teacherShortName", "minHrs", "maxHrs", "deptId", "snapshotId"],
    "timeTable": ["ttId", "day", "slotNo", "roomId", "classId", "subjectId", "teacherId", "batchId", "isFixed", "snapshotId"],
    "user": ["userId", "userName", "password"],
    "version": ["version"],
}


_INSERT_RE = re.compile(r"INSERT INTO `([^`]+)` VALUES\s*(.*?);\s*$", re.S)


def _split_top_level(values: str) -> List[str]:
    """Split a string of ``(...),(...),(...)`` tuples at the top level only.

    Parentheses inside string literals are honoured.
    """
    out: List[str] = []
    depth = 0
    in_string = False
    escape = False
    start = 0
    for i, ch in enumerate(values):
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == "'":
                in_string = False
            continue
        if ch == "'":
            in_string = True
            continue
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                out.append(values[start:i])
    return out


def _split_fields(tuple_body: str) -> List[Optional[str]]:
    """Split a single tuple body (without surrounding parens) into raw fields."""
    fields: List[Optional[str]] = []
    buf: List[str] = []
    in_string = False
    escape = False
    for ch in tuple_body:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
                buf.append(ch)
            elif ch == "'":
                in_string = False
                buf.append(ch)
            else:
                buf.append(ch)
            continue
        if ch == "'":
            in_string = True
            buf.append(ch)
            continue
        if ch == ",":
            fields.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    fields.append("".join(buf).strip())

    out: List[Optional[str]] = []
    for f in fields:
        if f == "NULL":
            out.append(None)
        elif f.startswith("'") and f.endswith("'"):
            inner = f[1:-1]
            inner = inner.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
            out.append(inner)
        else:
            out.append(f)
    return out


def _coerce(value: Optional[str]) -> Optional[object]:
    if value is None:
        return None
    if value == "":
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


@dataclass
class TaasikaData:
    snapshot_id: int
    tables: Dict[str, List[dict]] = field(default_factory=dict)

    def rows(self, table: str) -> List[dict]:
        return self.tables.get(table, [])

    def filtered(self, table: str) -> List[dict]:
        """Rows for the chosen snapshot (or all rows for tables w/o snapshot)."""
        cols = TABLE_COLUMNS.get(table, [])
        rows = self.tables.get(table, [])
        if "snapshotId" in cols:
            return [r for r in rows if r.get("snapshotId") == self.snapshot_id]
        return rows


def load(sql_path: Path = SQL_PATH_DEFAULT, snapshot_id: int = 240, tables: Optional[Iterable[str]] = None) -> TaasikaData:
    wanted = set(tables) if tables else set(TABLE_COLUMNS)
    parsed: Dict[str, List[dict]] = {t: [] for t in wanted}

    with sql_path.open("r", encoding="utf-8", errors="replace") as f:
        buf: List[str] = []
        for line in f:
            if not buf and not line.startswith("INSERT INTO `"):
                continue
            buf.append(line)
            if line.rstrip().endswith(";"):
                statement = "".join(buf)
                buf = []
                m = _INSERT_RE.match(statement)
                if not m:
                    continue
                table = m.group(1)
                if table not in wanted:
                    continue
                cols = TABLE_COLUMNS.get(table)
                if not cols:
                    continue
                values_part = m.group(2).strip()
                tuples = _split_top_level(values_part)
                for tup in tuples:
                    fields = _split_fields(tup)
                    if len(fields) != len(cols):
                        continue
                    row = {col: _coerce(val) for col, val in zip(cols, fields)}
                    parsed[table].append(row)

    return TaasikaData(snapshot_id=snapshot_id, tables=parsed)


if __name__ == "__main__":
    import json
    import sys

    snap = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    data = load(snapshot_id=snap)
    summary = {table: len(data.filtered(table)) for table in TABLE_COLUMNS}
    print(json.dumps({"snapshot": snap, "rows_for_snapshot": summary}, indent=2))
