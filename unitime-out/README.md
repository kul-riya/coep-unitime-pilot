# UniTime XML Inputs - Even Sem 2025-26 (COEP)

This directory holds 15 UniTime XML files generated from
`taasika2-foss-26jan26.sql/taasika2-foss-26jan26.sql`, snapshot
`240 - 'published-19jan26'` (Even Sem 25-26, effective 19 Jan 2026).

All files are ready to be loaded via UniTime's
**Administration > Academic Sessions > Data Exchange** page.

## Session identifiers

| Field   | Value |
| ------- | ----- |
| Campus  | `COEP` |
| Term    | `Spr` |
| Year    | `2026` |
| Source snapshot | `240 - 'published-19jan26'` |
| Source SQL | `taasika2-foss-26jan26.sql/taasika2-foss-26jan26.sql` |
| Working week | Monday-Sunday (M, T, W, Th, F, S, Su) |
| Day | 08:30 - 19:30, 11 x 60-minute slots |
| Session start | 2026-01-19 |
| Class end | 2026-04-30 |
| Exam start | 2026-05-04 |
| Session end | 2026-05-22 |
| Holidays | 2026-01-26, 2026-03-03, 2026-03-14, 2026-04-03, 2026-04-14, 2026-05-01 |

## Recommended UniTime import order

Files **must** be imported in this order because each one references entities
defined by an earlier file:

1. `sessionSetup.xml`           - creates the academic session, managers,
   departments, subject areas, solver groups, date patterns, time patterns,
   and exam periods. Nothing else can be imported until this exists.
2. `academicArea.xml`           - 2 areas (`BT` = B.Tech, `MT` = M.Tech).
3. `academicClassification.xml` - 5 year codes (`FY`, `SY`, `TY`, `BT`, `MT`).
4. `Major.xml`                  - 15 majors (CE / IT / IS / AI / DS / MDM /
   MIN / RES / OE / AIMA / AIML / PP / WD / PPS).
5. `Minor.xml`                  - empty stub; Taasika models minors as a
   posMajor inside the BT area, so no minors are produced.
6. `studentGroup.xml`           - one group per Taasika class (43) and per
   batch (165), code = Taasika short name.
7. `buildingRoomImport.xml`     - 45 rooms grouped into 7 inferred buildings:
   `AC` (Academic Complex), `CSED` (CSE Dept), `ENTCX` (ENTC Extension),
   `NCSE` (New CSE Building), `BHAU` (Bhau Institute), `ONL` (Online), and
   `UNAV` (Unavailable lab pool).
8. `roomSharing.xml`            - assigns every room to dept `0101` and marks
   weekday 12:30-13:30 as **LUNCH** (derived from 51 `fixedEntry` LUNCH rows
   in the snapshot) plus the weekend as unavailable by default.
9. `travelTimes.xml`            - 5 min between buildings, 3 min between
   CSED and the New CSE Building.  Override after import if needed.
10. `staff.xml`                 - 113 instructors with `positionType`
    derived from each teacher's `minHrs`/`maxHrs` envelope.
11. `courseCatalog.xml`         - 184 courses across 3 subject areas (`CS`,
    `MT`, `IFC`).  Lec subjects and their matching Lab / Tut subjects in
    Taasika (e.g. `CN` + `CN-Lab`, `SIC` + `SIC-Lab`, `OOPD` + `OOPD-Lab`) are
    merged into a single UniTime course.  Credits follow the Indian formula
    `1 cr / lec hr + 0.5 cr / lab hr`, so a 3-hr Lec + 2-hr Lab subject pair
    becomes a 4-credit course.
12. `courseOffering.xml`        - 63 offerings.  Each merged Lec+Lab course
    has one `<config>` with two `<subpart>`s (`Lec` and `Lab`); the offering
    holds one `<class type="Lec">` per Taasika class
    (subjectClassTeacher) and one `<class type="Lab">` per Taasika batch
    (subjectBatchTeacher).  Class ids use the human-readable UniTime format
    `"<area> <courseNbr> <type> <suffix>"` (e.g. `CS 110 Lab 3`), and every
    class carries `studentScheduling="true"`, `displayInScheduleBook="true"`,
    and `cancelled="false"`.  Times are intentionally left blank for UniTime
    to solve.  Rooms in `subjectRoom` / `classRoom` / `batchRoom` are kept
    as preferences (not pre-assignments).
13. `studentInfo.xml`           - 2,130 mock students, named with
    Indian-style first / last names, mapped to area + classification + major
    + studentGroup of their class and (round-robin) batch.
14. `studentRequest.xml`        - one course request per offered subject for
    each mock student (derived from their class's `subjectClassTeacher` rows
    + their batch's `subjectBatchTeacher` rows).
15. `studentenrollments.xml`    - direct Lec + Lab section enrolment for
    each mock student, matched to the section suffix produced in
    `courseOffering.xml`.

## Local UniTime 4.9 room-loader note

In UniTime 4.9, `buildingRoomImport.xml` loads the external room catalogue;
it does not create the internal instructional-room records read by the course
solver.  For the local MySQL pilot, generate and run the supplied loader after
importing `buildingRoomImport.xml` and before importing `roomSharing.xml`:

```powershell
python scripts\gen_instructional_room_sql.py
mysql -u timetable -p timetable < unitime-out\load_instructional_rooms.sql
```

After the loader completes, re-import `roomSharing.xml` and
`courseOffering.xml` so room availability and class room preferences are
linked to the newly created instructional rooms.

## Decisions taken automatically

The Taasika dump does not store some fields UniTime requires.  We chose the
following defaults; override them after import if your university uses
different values:

| Decision | Default |
| -------- | ------- |
| Department codes | `0101`=CEIT (Taasika dept 1), `0102`=ENTC (2), `0103`=INSTRU (3), `0104`=IT/CEIT (4) |
| Subject area scheme | Three areas split by program: `CS` (B.Tech CSE/IT), `MT` (M.Tech), `IFC` (Interdisciplinary). No `VSEC` area because no subject in snapshot 240 was tagged as VSEC. |
| Course numbering | Per-area sequential numbers starting at 101, ordered by `subjectId`.  Lab subjects that pair with a Lec subject do *not* consume a number - they share the Lec's number.  Stable across re-runs of the same snapshot. |
| Lec+Lab pairing | A Lab/Tut subject is merged into its Lec partner if `lab.shortName == lec.shortName + "-Lab"` (or `"Lab"`, `" Lab"`, `"-Tut"`, `" Tut"`, `"-Tutorial"`, `" Tutorial"`).  67 candidate pairs in snapshot 240; 48 actually used after dropping the 19 Lec subjects with no `subjectClassTeacher` rows. |
| Course credits | Paired: `lec.eachSlot * lec.nSlots + 0.5 * lab.eachSlot * lab.nSlots` (Indian engineering convention).  Unpaired: `eachSlot * nSlots` (lec-only) or `0.5 * eachSlot * nSlots` (lab-only).  Minimum 1. |
| Building inference | Heuristic on `roomName` and `roomShortName`. Online classrooms get a virtual building, "Unavailable" labs go into their own pool. |
| Room departments | All 49 rooms 100% assigned to `0101` (the CSE-centric snapshot has no ENTC/INSTRU teachers). |
| Instructor position | Mapped from `minHrs`: `<=6` PROF, `<=12` ASSOC_PROF, `<=14` ASST_PROF, else ASST_PROF; (`min=0`, `max=0`) -> ADJUNCT; (`min=0`, `max=24`) -> VISITOR. |
| LUNCH block | Hard unavailability on every room, MTWThF 12:30-13:30 (matches the 51 LUNCH fixedEntry rows in snapshot 240). |
| Subjects skipped | 121 of 184 controlling (lec) subjects have no `subjectClassTeacher` and no `subjectBatchTeacher` row in snapshot 240, so they were intentionally omitted from `courseOffering.xml` while still appearing in `courseCatalog.xml`. |
| Mock student naming | `externalId = <classShortName>-S<index>`, first name from a fixed 30-name list, last name from a 15-surname list. |

## Evaluate a solution

After exporting a timetable from UniTime (**Course Timetabling Solver → Export**
CSV, or Timetable Grid export), score it against the constraints in this
directory:

```powershell
python scripts\eval_timetable_kpis.py
python scripts\eval_timetable_kpis.py --csv solutions\COEPSpr2026_v2.csv --out solutions\kpi_report.json
```

The script prints a console summary and writes `solutions/kpi_report.json`.

| Score | Meaning |
| ----- | ------- |
| Hard feasibility (0–100) | Equal-weight average of coverage, time-pattern fidelity, date pattern, room capacity, lunch/weekend, instructor/room double-booking, and student conflict rates |
| Preference score (0–100) | Average of room-preference hit rate and instructor-identity match rate |
| Efficiency metrics | Instructor weekly load (mean/stdev), travel-gap violations, UNAV/ONL usage, early/mid/late slot spread, back-to-back density |

Hard failures and preference misses include up to 8 example rows each for debugging.

## Re-generating

The full pipeline is reproducible from the SQL.  From the repo root:

```powershell
python scripts\gen_session_setup.py
python scripts\gen_academic.py
python scripts\gen_buildings.py
python scripts\gen_staff.py
python scripts\gen_course_catalog.py
python scripts\gen_course_offering.py
python scripts\gen_students.py
python scripts\gen_preferences.py
```

To target a different snapshot (for example `241 - 'draft-19jan26-onwards'`),
edit the `snapshot_id=240` argument inside each `gen_*.py` script (or override
via the loader's `load(snapshot_id=...)` call).

## What is intentionally not in these files

- **Pre-assigned times.**  We are asking UniTime to solve the timetable, so
  every class section is left without a `<time>` element.  The existing 661
  `timeTable` rows in Taasika are not imported as preferences.
- **Fixed-section distribution constraints.** `preferences.xml` includes
  required `SAME_STUDENTS` constraints for lecture sections with an identical
  simulated cohort and required `DIFFERENT_TIME` constraints for every other
  pair of fixed enrolled sections that share at least one student. These make
  the timetable respect the simulated roster even when UniTime could otherwise
  re-section students into alternative classes.
- **Exam definitions for individual courses.**  `examinationPeriods` are
  declared in `sessionSetup.xml` but no per-course `<exam>` elements are
  emitted.  Taasika does not model final/midterm exams.
- **Per-subject reservation rules.**  Open-elective and reserved-cohort
  classes (`MT-OE`, `FY-Reserved1..3`, `SY-OE1`, `SY-OE2`) are tagged via
  their major but no `<reservation>` XML is produced.
