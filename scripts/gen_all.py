"""Master generation pipeline for all UniTime XML input files (1 to 16).

Executes all generator modules in dependency order and then runs validation
and verification scripts.

Usage:
  python scripts/gen_all.py
  python scripts/gen_all.py --term=Spr6
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure scripts directory is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import taasika_loader

import gen_session_setup
import gen_academic
import gen_buildings
import gen_staff
import gen_course_catalog
import gen_course_offering
import gen_preferences
import gen_students
import validate_xmls
import validate_course_offering
import verify_time_patterns

DEFAULT_TERM = "Spr"

GENERATORS = [
    ("1sessionSetup.xml", gen_session_setup.main),
    ("2academicArea.xml .. 6studentGroup.xml", gen_academic.main),
    ("7buildingRoomImport.xml .. 9travelTimes.xml", gen_buildings.main),
    ("10staff.xml", gen_staff.main),
    ("11courseCatalog.xml", gen_course_catalog.main),
    ("12courseOffering.xml", gen_course_offering.main),
    ("13preferences.xml", gen_preferences.main),
    ("14studentInfo.xml .. 16studentenrollments.xml", gen_students.main),
]


def run_pipeline(term: str = DEFAULT_TERM) -> int:
    start_time = time.time()
    print("=" * 70)
    print(f"  COEP UniTime XML Generation Pipeline (Files 1 to 16, Term: {term})")
    print("=" * 70)

    for step_num, (desc, func) in enumerate(GENERATORS, start=1):
        print(f"\n[{step_num}/{len(GENERATORS)}] Generating {desc} (term={term})...")
        try:
            func(term=term)
        except Exception as e:
            print(f"ERROR during {desc}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    print("\n" + "=" * 70)
    print("  Running Validation and Verification Checks")
    print("=" * 70 + "\n")

    print("--- 1. XML Well-Formedness Check (validate_xmls.py) ---")
    val_xml_code = validate_xmls.main()

    print("\n--- 2. Course Offering Structure Check (validate_course_offering.py) ---")
    val_off_code = validate_course_offering.main()

    print("\n--- 3. Time Patterns Verification (verify_time_patterns.py) ---")
    ver_time_code = verify_time_patterns.main()

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    if val_xml_code == 0 and val_off_code == 0 and ver_time_code == 0:
        print(f"  ALL GENERATION & VALIDATION COMPLETED SUCCESSFULLY in {elapsed:.2f}s (term={term})")
        print("=" * 70)
        return 0
    else:
        print(f"  PIPELINE FINISHED WITH ISSUES in {elapsed:.2f}s (term={term})", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate all UniTime XML files (1 to 16) and run validation/verification."
    )
    parser.add_argument(
        "--term",
        default=DEFAULT_TERM,
        help="UniTime academic term name (e.g. Spr, Spr6). Default: %(default)s",
    )
    parser.add_argument(
        "--sql",
        help="Path to the Taasika SQL dump file to use",
    )
    parser.add_argument(
        "--snapshot",
        type=int,
        help="Snapshot ID to generate XMLs for",
    )
    args = parser.parse_args()

    sql_path = None
    if args.sql:
        sql_path = Path(args.sql).resolve()
    else:
        db_dir = SCRIPTS_DIR.parent / "taasika-db"
        sql_files = list(db_dir.glob("*.sql")) if db_dir.exists() else []
        if not sql_files:
            print("No SQL files found in taasika-db/ directory.")
            sql_path_str = input("Enter path to SQL dump: ").strip()
            if not sql_path_str:
                print("No SQL file provided. Exiting.")
                return 1
            sql_path = Path(sql_path_str).resolve()
        elif len(sql_files) == 1:
            sql_path = sql_files[0]
            print(f"Using only available SQL file: {sql_path.name}")
        else:
            print("Available SQL files:")
            for i, f in enumerate(sql_files, start=1):
                print(f"  [{i}] {f.name}")
            choice = input(f"Select SQL file [1-{len(sql_files)}]: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sql_files):
                    sql_path = sql_files[idx]
                else:
                    raise ValueError()
            except ValueError:
                print("Invalid choice. Exiting.")
                return 1

    snapshot_id = args.snapshot
    if not snapshot_id:
        print(f"Loading snapshots from {sql_path.name}...")
        try:
            snap_data = taasika_loader.load(sql_path=sql_path, tables=["snapshot"])
            snapshots = snap_data.rows("snapshot")
        except Exception as e:
            print(f"Error reading snapshots: {e}")
            return 1
            
        if not snapshots:
            print("No snapshots found in the database.")
            snap_str = input("Enter Snapshot ID manually: ").strip()
            if not snap_str:
                return 1
            snapshot_id = int(snap_str)
        else:
            print("Available Snapshots:")
            for s in snapshots:
                print(f"  ID: {s.get('snapshotId')} | Name: {s.get('snapshotName')} | Date: {s.get('createTime')}")
            
            snap_choice = input("Enter Snapshot ID to use: ").strip()
            try:
                snapshot_id = int(snap_choice)
            except ValueError:
                print("Invalid Snapshot ID. Exiting.")
                return 1

    print(f"\nConfiguring generator to use {sql_path.name} (Snapshot {snapshot_id})")
    taasika_loader.set_global_config(sql_path, snapshot_id)

    return run_pipeline(term=args.term)


if __name__ == "__main__":
    sys.exit(main())
