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
    args = parser.parse_args()
    return run_pipeline(term=args.term)


if __name__ == "__main__":
    sys.exit(main())
