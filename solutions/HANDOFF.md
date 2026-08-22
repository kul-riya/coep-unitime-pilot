# Handoff summary — COEP UniTime pilot

Use this to continue in a **new chat**. Repo: `d:\Riya\College\btech` (branch historically `dev_riya`).

## Goal
Migrate COEP Even Sem 2025–26 (Taasika snapshot **240**) into UniTime, solve a timetable, evaluate quality, show **subject short codes** (CN, OOPD) on the grid.

## Key paths
| Path | Role |
|------|------|
| `taasika2-foss-26jan26.sql/taasika2-foss-26jan26.sql` | Source dump |
| `unitime-out/` | Import XMLs + README (import order) |
| `scripts/` | Generators + KPI + relabel |
| `solutions/COEPSpr2026_v4.csv` | Latest export (**relabeled** to short codes) |
| `solutions/COEPSpr2026_v4_numeric.csv` | Pre-relabel backup |
| `solutions/timetable_v4.html` | HTML grid with subject codes |
| `solutions/kpi_report.json` | Last full KPI (was for v3-era data) |
| `solutions/course_type_report.md` | Course types / elective rules |
| `solutions/subject_batch_map.md` | Subject→batch mapping |

## Student model (current)
- IDs: `61yy03aaa` — yy=`01` FY … `04` BT, `05` MT; aaa=`001`–`500` (400 CE + 100 AIML)
- 2130 students total (2000 B.Tech + 130 MT)
- No divisions: defaults mandatory; electives (DE/OE/MDM/HONOR/MINOR) pick **one**, equal split
- OE/MDM: assume **5 college-wide options** (CSE course + OTHER placeholders); only CSE option gets UniTime enrollment
- Planned slots (not fully enforced in UniTime yet): MDM Mon/Tue 16:30–18:30; OE Wed/Thu 16:30–17:30
- `studentInfo.xml` uses `incremental="true"` and **omits studentGroups** (avoids Hibernate `TransientObjectException`)

## Import order (critical)
See `unitime-out/README.md`. Must include **`preferences.xml` after `courseOffering.xml`**. Without it, solver loads ~0–17 classes instead of 254.

1. sessionSetup → academic* → Major/Minor → studentGroup  
2. buildings → roomSharing → travelTimes → staff  
3. courseCatalog → **courseOffering** → **preferences**  
4. studentInfo → studentRequest → studentenrollments  

Course numbers are now **Taasika shortNames** (`CN`, `DS-FY`, …). Class ids like `CN Lec 1`.

## Timetable / codes issue
- UniTime native export/PDF (`timetable_v3*`, raw v4) still showed `CS 102` because the solved DB/export predated successful short-name apply.
- Offline fix: `python scripts/relabel_timetable_csv.py` → updates CSV + `timetable_v4.html`.
- For UniTime itself to export short codes: re-import catalog + offering + preferences, **new solve**, new export (don’t reload old saved TT).

## Why `CS CN Lec 2` is MTWThF (5 days) but should be 3
- CN Lec `minPerWeek=180` → preferences require pattern **`3 x 60`** (e.g. MWF).
- Solution has Lec1=`TTh` (2 days) and Lec2=`MTWThF` (5 days) — **both wrong**.
- Root cause: class time pattern in the solved session is not actually bound to `3 x 60` (prefs missing/mismatched after courseNbr rename, or required prefs not applied). SessionSetup correctly restricts `3 x 60` to 3-day codes only; getting `MTWThF` means the class was treated as **`5 x 60`**.
- **Next fix:** re-import `preferences.xml` (course=`CN` not `109`), confirm in UI each CN Lec subpart shows pattern `3 x 60`, reload solver, resolve. Optionally drop Saturday from patterns / raise time-pref weight.

## KPI vs UniTime solver panel
- Our KPI (`eval_timetable_kpis.py`) scores overlaps using **`studentenrollments.xml`** + preferred rooms from offerings.
- UniTime panel “Student conflicts: 0” / “prefs 100%” uses **solver demand mode** + internal soft prefs — often **not** the enrollment XML. Overall value ~1.74 was mostly **room size penalty**.
- Last noted hard score ~89 with ~1659/2130 students conflicting under dense new enrollments; v2 (old division roster) had fewer student conflicts but worse pattern fidelity before day-code fix.

## Generators to know
| Script | Output |
|--------|--------|
| `gen_session_setup.py` | Time patterns with day codes filtered by `nbrMeetings` |
| `gen_course_catalog.py` | ShortName as `courseNumber` |
| `gen_course_offering.py` | 58 offerings / 244 classes (v5, after elective Lec+Lab merge fix) |
| `gen_preferences.py` | Required time+date prefs |
| `gen_students.py` | Info / requests / enrollments |
| `relabel_timetable_csv.py` | Numeric→short COURSE remap + HTML |
| `eval_timetable_kpis.py` | KPI JSON |

## Open / next work
1. Fix time-pattern binding so 3×60 never becomes MTWThF (re-import prefs + verify UI + resolve).
2. Re-run KPI on coded `COEPSpr2026_v4.csv` vs current `unitime-out`.
3. Reduce student conflicts (solver student-conflict weight; OE/MDM fixed slots; fewer overlapping FY stacks).
4. Ban or discourage Saturday; reduce UNAV/ONL (~27%).
5. Enforce MDM/OE hard-coded college-wide slots in UniTime (distribution prefs or exact times).
6. Optional: regenerate PDF (reportlab install failed on this machine; HTML exists).
7. **Done (this session):** DE/Honor/PSEC electives (`DE2-BCT`, `DE2-DSci`, `DE2-ASP`, `DE4-GIS`, `DE4-GPU`) were
   mislabeled as standalone 180-min **Lab** offerings instead of merged **Lec (180) + Lab (120)** — root cause was
   `classifications.py::find_course_pairs()` refusing to pair a lecture with its `-Lab` companion whenever the
   lecture itself had `batches=1` (true for batch-registered electives, unlike ordinary courses where only the
   lab has `batches=1`). Fixed in `classifications.py`, `gen_course_offering.py`, `gen_course_catalog.py`
   (`isLab` field), and the parallel logic in `verify_time_patterns.py`. Regenerated `courseCatalog.xml`
   (165 courses, 67 merged pairs), `courseOffering.xml` (58 offerings, was 63 — 5 offerings absorbed into their
   lecture partner), `preferences.xml` (86 subparts, `verify_time_patterns.py` now reports a clean 86/86 match),
   and student XML files. `DE4-IBCS`/`DE4-IBC-Lab` still does **not** merge — that's a separate pre-existing
   Taasika shortName typo (`IBCS` vs `IBC`), not this bug; needs either a Taasika rename or a manual alias in
   `classifications.py` if it should also merge.
   Because `courseOffering.xml` is a non-incremental (full-replace) import, simply re-importing it will drop the
   5 stale standalone "-Lab" offerings automatically — no manual deletion needed in UniTime.
   **Still needs:** fresh UniTime import (courseCatalog → courseOffering → preferences → student files) and a
   fresh solve; `solutions/kpi_report.json` in this repo currently compares the new expected structure against
   the **old, stale** `COEPSpr2026_v4.csv` solve, so its "missing assignment" / time-pattern failures for the
   newly-merged courses are expected until a new solve + export is produced (see `UNITIME_RESOLVE_CHECKLIST.md`).

## Quick verify commands
```powershell
cd d:\Riya\College\btech
python scripts\relabel_timetable_csv.py
python scripts\eval_timetable_kpis.py --csv solutions\COEPSpr2026_v4.csv --out solutions\kpi_report.json
```
