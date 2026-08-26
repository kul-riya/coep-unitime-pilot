"""Import generated UniTime XML via the Data Exchange API.

Reference: https://help.unitime.org/manuals/api#9data-exchange

    POST {base}/api/exchange
    Content-Type: application/xml;charset=UTF-8
    Auth: HTTP Basic

Session, type, and campus are read from the XML itself. Default target:

    http://103.76.102.113:8080/UniTime   (user/password: admin)

After ``staff.xml``, UniTime still needs **Courses → Input Data → Instructors
→ Manage Instructor List** before class instructors resolve. After
``buildingRoomImport.xml``, run **Administration → Academic Sessions →
Buildings → Update Data**.

Usage (existing session with a saved timetable — recommended):
    python scripts/import_unitime.py
    python scripts/import_unitime.py --dry-run

Do not purge while a timetable is saved/committed. UniTime throws
Hibernate TransientObjectException because the solution still references
CourseOffering rows. Uncommit+delete the solution first if you really
need a wipe:

    Courses → Timetabling → Timetables → select solution → Uncommit → Delete
    python scripts/import_unitime.py --full --purge

Other:
    python scripts/import_unitime.py --from 11
    python scripts/import_unitime.py --only 12courseOffering.xml 13preferences.xml
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "unitime-out"

DEFAULT_BASE = os.environ.get("UNITIME_URL", "http://103.76.102.113:8080/UniTime")
DEFAULT_USER = os.environ.get("UNITIME_USER", "admin")
DEFAULT_PASSWORD = os.environ.get("UNITIME_PASSWORD", "admin")

# Full Data Exchange order (matches unitime-out/README.md).
IMPORT_STEPS: list[tuple[str, str]] = [
    ("purge", "courseOffering-PURGE-all.xml"),
    ("1", "1sessionSetup.xml"),
    ("2", "2academicArea.xml"),
    ("3", "3academicClassification.xml"),
    ("4", "4Major.xml"),
    ("5", "5Minor.xml"),
    ("6", "6studentGroup.xml"),
    ("7", "7buildingRoomImport.xml"),
    ("8", "8roomSharing.xml"),
    ("9", "9travelTimes.xml"),
    ("10", "10staff.xml"),
    ("11", "11courseCatalog.xml"),
    ("12", "12courseOffering.xml"),
    ("13", "13preferences.xml"),
    ("14", "14studentInfo.xml"),
    ("15", "15studentRequest.xml"),
    ("16", "16studentenrollments.xml"),
]

_UI_NOTES = {
    "7buildingRoomImport.xml": (
        "After rooms: Administration → Academic Sessions → Buildings → Update Data"
    ),
    "10staff.xml": (
        "After staff: Courses → Input Data → Instructors → Manage Instructor List"
    ),
}

_SAVED_TT_HINT = (
    "A saved/committed timetable still references these offerings, so UniTime "
    "cannot delete them (Hibernate TransientObjectException).\n"
    "Uncommit and delete the saved solution, then retry purge if you need a wipe:\n"
    "  Courses → Timetabling → Timetables → select solution → Uncommit → Delete\n"
    "Otherwise skip purge and update in place:\n"
    "  python scripts/import_unitime.py --from 11"
)

_ERROR_RE = re.compile(
    r"error|exception|failed|fatal",
    re.I,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _base_url(url: str) -> str:
    return url.rstrip("/")


def _exchange_url(base: str) -> str:
    return f"{_base_url(base)}/api/exchange"


def _html_to_text(html: str) -> str:
    text = html.replace("<br>", "\n").replace("<br/>", "\n").replace("</p>", "\n")
    text = _TAG_RE.sub("", text)
    lines = [ln.replace("\xa0", " ").strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _looks_failed(log: str, status: int = 200) -> bool:
    if status >= 400:
        return True
    lowered = log.lower()
    if "transaction rolled back" in lowered or "import failed" in lowered:
        return True
    # UniTime often prints a Java stack trace for a skipped/truncated row
    # and still commits. HTTP 200 + committed = success.
    if "transaction committed" in lowered:
        return False
    return False


def _is_saved_timetable_hibernate(status: int, body: str, log: str) -> bool:
    blob = f"{body}\n{log}"
    return status >= 400 and "TransientObjectException" in blob and "CourseOffering" in blob


def import_xml(
    path: Path,
    *,
    base: str,
    user: str,
    password: str,
    timeout: int,
    insecure: bool,
) -> tuple[int, str]:
    data = path.read_bytes()
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        _exchange_url(base),
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/xml;charset=UTF-8",
            "Authorization": f"Basic {token}",
        },
    )
    if insecure:
        ctx = ssl._create_unverified_context()
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    else:
        opener = urllib.request.build_opener()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        return exc.code, body


def _steps(args: argparse.Namespace) -> list[tuple[str, Path]]:
    if args.only:
        out: list[tuple[str, Path]] = []
        for name in args.only:
            path = Path(name)
            if not path.is_file():
                path = OUT_DIR / name
            out.append((path.name, path))
        return out

    selected: list[tuple[str, Path]] = []
    from_step = args.from_step
    if from_step is None and not args.full:
        from_step = "11"
    started = from_step is None
    for key, filename in IMPORT_STEPS:
        if key == "purge" and not args.purge:
            continue
        if not started:
            if key == from_step or filename == from_step:
                started = True
            else:
                continue
        selected.append((filename, OUT_DIR / filename))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Import unitime-out XML via /api/exchange")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="UniTime app root")
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--timeout", type=int, default=300, help="Per-file HTTP timeout (seconds)")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate verify")
    parser.add_argument("--dry-run", action="store_true", help="Print the import order and exit")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Import session setup through students (default is catalog→students only)",
    )
    parser.add_argument(
        "--purge",
        dest="purge",
        action="store_true",
        default=False,
        help="Delete offerings first (fails if a timetable is saved/committed)",
    )
    parser.add_argument("--no-purge", dest="purge", action="store_false")
    parser.add_argument("--from", dest="from_step", default=None, help="Start at this step key or filename")
    parser.add_argument("--only", nargs="+", help="Import only these files (paths or names under unitime-out)")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    steps = _steps(args)
    print(f"UniTime Data Exchange  {_exchange_url(args.base_url)}")
    print(f"Files: {len(steps)}   user={args.user}")
    for filename, path in steps:
        mark = "OK" if path.is_file() else "MISSING"
        print(f"  [{mark}] {filename}  ({path.stat().st_size:,} bytes)" if path.is_file() else f"  [{mark}] {filename}")
    if args.dry_run:
        return 0

    missing = [p for _, p in steps if not p.is_file()]
    if missing:
        print("Missing files:", ", ".join(p.name for p in missing), file=sys.stderr)
        return 1

    failures: list[str] = []
    for filename, path in steps:
        print(f"\n=== importing {filename} ({path.stat().st_size:,} bytes) ===")
        t0 = time.perf_counter()
        try:
            status, body = import_xml(
                path,
                base=args.base_url,
                user=args.user,
                password=args.password,
                timeout=args.timeout,
                insecure=args.insecure,
            )
        except urllib.error.URLError as exc:
            print(f"FAIL network: {exc}", file=sys.stderr)
            failures.append(filename)
            if not args.continue_on_error:
                return 1
            continue
        elapsed = time.perf_counter() - t0
        log = _html_to_text(body)
        preview = "\n".join(log.splitlines()[-12:])
        print(f"HTTP {status}  {elapsed:.1f}s")
        if preview:
            print(preview)
        failed = _looks_failed(log, status)
        if failed:
            print(f"FAIL {filename}", file=sys.stderr)
            if status == 403 and "Api Data Exchange Connector" in (body + log):
                print(
                    "The admin user is missing permission 'Api Data Exchange Connector'.\n"
                    "In UniTime: Administration → Roles → Administrator → enable\n"
                    "'Api Data Exchange Connector', then re-run this script.",
                    file=sys.stderr,
                )
            saved_tt = _is_saved_timetable_hibernate(status, body, log)
            if saved_tt:
                print(_SAVED_TT_HINT, file=sys.stderr)
            skip_purge = saved_tt and filename.startswith("courseOffering-PURGE")
            if skip_purge:
                print("Skipping purge; continuing with offering update.", file=sys.stderr)
                continue
            failures.append(filename)
            if not args.continue_on_error:
                return 1
        else:
            print(f"OK {filename}")
        note = _UI_NOTES.get(filename)
        if note:
            print(f"NOTE {note}")

    if failures:
        print(f"\nFinished with {len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("\nAll imports completed. Reload the course timetabling solver.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
