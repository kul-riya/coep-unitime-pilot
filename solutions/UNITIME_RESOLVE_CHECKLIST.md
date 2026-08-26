# UniTime re-import and re-solve checklist (COEP Spr 2026)

Use after regenerating XML from the repo (`python scripts/gen_preferences.py`,
`python scripts/gen_students.py`).

> **v5 update:** `classifications.py`/`gen_course_offering.py`/`gen_course_catalog.py` had a bug where
> batch-registered elective lectures (`DE2-BCT`, `DE2-DSci`, `DE2-ASP`, `DE4-GIS`, `DE4-GPU`) were emitted as
> standalone 180-min **Lab** offerings instead of merging with their `-Lab` companion into one **Lec(180)+Lab(120)**
> course. This is now fixed — regenerate `courseCatalog.xml` and `courseOffering.xml` too, not just
> `preferences.xml`/`studentenrollments.xml`. Import **`unitime-out/courseOffering-PURGE-v5.xml` first** to delete
> the 5 now-stale standalone `-Lab` offering ids (`32646`, `32703`, `32705`, `32707`, `32717`) — same pattern as
> the earlier `courseOffering-PURGE.xml` used for the courseNbr rename; don't assume a plain re-import replaces
> them.

## 1. Data Exchange import order

Administration → Academic Sessions → Data Exchange (session **COEP / Spr / 2026**):

**Before step 12**, confirm these one-time UI steps on a new session:

| After import | Required UI step |
|--------------|------------------|
| Step 7 `buildingRoomImport.xml` | **Administration → Academic Sessions → Buildings → Update Data** (rooms are not usable until this) |
| Step 10 `staff.xml` | **Courses → Input Data → Instructors → Manage Instructor List** (pull staff into instructors; required before `preferences.xml` if it lists instructors) |

> **courseOffering.xml import tips (Hibernate `TransientObjectException`):**
> - **Stack trace reading:** if the failure is in
>   `deleteUnmatchedInstructionalOfferings` → `deleteInstructionalOffering` →
>   `flush`, CS CoI was **inserted successfully**; UniTime then tried to delete
>   *other* session offerings not listed in your file (default non-incremental
>   mode). That cleanup flush hit a Hibernate bug when mixed with the new insert.
> - **Fix:** all generated offering files now set **`incremental="true"`** on the
>   root `<offerings>` element. Re-import with the regenerated XML. Incremental
>   mode only creates/updates offerings listed in the file — it does **not** mass-
>   delete everything else in the session.
> - Use `<offering id="taasika-io-…">` / `<course id="taasika-subject-…">`
>   (different ids, matching `courseCatalog.xml`), `<courseCredit …/>` on each
> - Class-level `<instructor id="taasika-teacher-…"/>` is **on** each class again
>   (needed for UniTime to show instructors on the exported timetable). Re-import
>   `staff.xml`, run **Manage Instructor List**, then re-import `courseOffering.xml`.
>   Adjuncts use `positionType="ADJUNCT"` (UI label **Adjunct Faculty**); `(Adjunct)`
>   is stripped from the person name.
> - To remove stale offerings explicitly, import a **purge** file first
>   (`courseOffering-PURGE-all.xml` or `courseOffering-PURGE-v5.xml` — both also
>   use `incremental="true"`), then import the real `courseOffering.xml`.
> - **Debug:** `courseOffering-minimal.xml` (CS CoI only) on a session that already
>   has other offerings requires `incremental="true"` (included in regenerated file).

| Step | File | Notes |
|------|------|-------|
| 10a | `unitime-out/courseOffering-PURGE-all.xml` | After any failed offering import — clears partial/legacy offerings |
| 10b | `unitime-out/courseOffering-PURGE-v5.xml` | If upgrading from pre-v5 merge fix — deletes 5 stale standalone `-Lab` offerings |
| 11 | `unitime-out/courseCatalog.xml` | **Required this round** — elective Lec+Lab merge fix changed course numbers |
| 12 | `unitime-out/courseOffering.xml` | 58 offerings, 260 classes (`action="insert"` for fresh session) |
| 13 | **`unitime-out/preferences.xml`** | **Required** — time + room prefs on every subpart/class |
| 14 | `unitime-out/studentInfo.xml` | incremental=true |
| 15 | `unitime-out/studentRequest.xml` | |
| 16 | `unitime-out/studentenrollments.xml` | **Before solver** — division-aware FY/TY sections |

## 2. Verify preferences in UI

For each sample course, open **Instructional Offering → Scheduling Subpart**:

| Course | Subpart | Required time pattern |
|--------|---------|----------------------|
| CN | Lec | `3 x 60` |
| FY-Reserved | Lec | `5 x 60` |
| DS-FY | Lec | `3 x 60` |
| DE2-BCT | Lec | `3 x 60` (was wrongly a standalone `1 x 180` Lab before the merge fix) |
| DE2-BCT | Lab | `1 x 120` |

Open **Class → Preferences** and confirm **roomPref** rows imported (primary = Required).

If patterns show “Arrange Hours” or wrong pattern, re-import `preferences.xml` **after**
`courseOffering.xml` and do not skip step 13.

## 3. Solver settings

Apply parameters from [`unitime-out/solver_parameters_recommended.txt`](../unitime-out/solver_parameters_recommended.txt):

- `General.JenrlMaxConflicts=0.0`
- `General.JenrlMaxConflictsWeaken=0.0`
- Raise `Lecture.HardStudentConflictWeight` and `Lecture.RoomPreferenceWeight`

## 4. Solve (fresh)

1. Course Timetabling → **Solver**
2. **Reload** — loads classes + prefs + enrollments (do **not** “Load saved timetable” from pre-rename era)
3. Confirm variable count ≈ **260** classes (not ~0–17)
4. **Start** / resolve until student conflicts and room prefs improve
5. **Commit** solution
6. Export CSV → save as `solutions/COEPSpr2026_v5.csv`

## 5. Offline KPI

```powershell
cd d:\Riya\College\btech
python scripts\relabel_timetable_csv.py solutions\COEPSpr2026_v5.csv
python scripts\eval_timetable_kpis.py --csv solutions\COEPSpr2026_v5.csv --out solutions\kpi_report.json
python scripts\verify_time_patterns.py
```

Expected improvements vs v4:

- `time_pattern_fidelity` reflects real 3×60 / 5×60 binding (not false 100%)
- `student_conflicts` lower with division-aware enrollments + hard Jenrl limit
- `room_preference` higher with `roomPref` in preferences.xml
