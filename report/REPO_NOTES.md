# REPO_NOTES.md — evidence map for the Semester VII report

Project: **taasika-v3** (automated university course timetabling for COEP Technological University).
Repository: `coep-unitime-pilot` (folder name predates the project name).
Remote: `git@github.com:kul-riya/coep-unitime-pilot.git` — https://github.com/kul-riya/coep-unitime-pilot

Everything below was read out of the working tree at commit `222f849` (branch `dev_mihir`) on the
pilot machine. Numbers marked **[verified]** were recomputed during this exploration; numbers marked
**[file]** are quoted from a committed artifact without re-running the producing command.

---

## 1. Repository structure

| Path | Contents |
|---|---|
| `scripts/` | 25 Python generators / validators / evaluators + `scripts/unitime_scripts/` (2 Jython scripts that run *inside* UniTime) |
| `unitime-out/` | Generated UniTime Data Exchange XML (16 numbered files) + `0gen_all/` (the current frozen dataset) + `0gen_all.zip` |
| `rl/` | Maven module `unitime-rl` (Java 17) + `python/unitime_rl` (Gymnasium/PPO) + `config/`, `instances/`, `models/`, `runs/` |
| `cpsolver/` | Sibling clone of UniTime's CPSolver, built and installed locally (`1.4-SNAPSHOT`) |
| `solutions/` | Exported timetables (CSV + solver XML) and KPI reports (JSON) |
| `taasika-db/` | `taasika2-foss-26jan26.sql`, `taasika3.sql` — the institutional source dumps |
| `compare/` | `240.txt`, `242.txt`, `245.txt`, `263.txt` — human-readable snapshot dumps from `inspect_snap.py` |
| root | `README.md`, `Sem6_BTech_Project_Report.pdf`, `UniTime_Project_Presentation.pptx`, schema PNGs, screenshots |

### Images already in the repo (usable as figures without fabrication)

| File | What it is |
|---|---|
| `taasika-schema.png` | Taasika ER schema (used as Figure 2 in the Sem VI report) |
| `unitime-schema.png` | UniTime ER schema (Figure 3 in the Sem VI report) |
| `Screenshot 2026-04-13 165841.png`, `image.png`, `image (1).png`, `image (2).png` | UniTime UI screenshots — **content not yet identified; must be opened and captioned truthfully or omitted** |

---

## 2. Version history (git)

30 commits, no tags, two authors, 2026-06-23 → 2026-10-08.

```
Mihir Shah  <mihirpkshah@gmail.com>   18 commits
Riya Kulkarni <riya.kulkarni.2803@gmail.com>  14 commits
```

Branches: `dev_mihir` (HEAD, == `origin/dev_mihir`), `dev_riya` (== `origin/HEAD`), `origin/spr4`.

| Date | Commit | Subject | Phase |
|---|---|---|---|
| 2026-06-23 | `8586fb6` | first commit | **Phase 1 — bootstrap** |
| 2026-06-23 | `8aee005` | README | |
| 2026-06-23 | `cddefd1` | generated solutions | |
| 2026-07-29 | `3234069` | Simulate preference-based student enrollments with `61yy03aaa` IDs and course-type reports | **Phase 2 — student simulation** |
| 2026-08-16 | `07f93d3` | student and time pattern update | |
| 2026-08-22 | `ef39b51` | Fix elective Lec+Lab pairing and courseOffering import for UniTime | |
| 2026-08-26 | `796f329` | changes part 2 | |
| 2026-08-26 | `567523d` | preferences | |
| 2026-08-29 | `2cbfa93` | term Spr5, MDM block scheduling, 2x120 course preference patterns | **Phase 3 — constraints** |
| 2026-08-29 | `deaa765` | master pipeline script (`gen_all.py`) to generate and validate all XML | |
| 2026-08-29 | `6645c7c` | persistence helpers + repair of null `SolverType` in `setup_lunch_breaks.py` | |
| 2026-08-29 | `397c8ce` | flexible time preference constraint system in `gen_preferences.py` | |
| 2026-08-29 | `1e024e7` | emit only matching slots instead of prohibiting others | |
| 2026-08-29 | `24a4d7f` | term Spr6 + `purge_uploaded_data.py` | |
| 2026-08-29 | `f9f9fe0` | rename `FY-Reserved` → `FY-Reserve`, update limits and enrollment mappings | |
| 2026-09-07 | `c74ac94` | Added complete taasika db sql | **Phase 4 — new snapshot** |
| 2026-09-09 | `942c24d` | integrate snapshot 263 data, update UniTime XML configurations | |
| 2026-09-11 | `c91c558` | improve timetable KPI evaluation; optional room-preference toggle | |
| 2026-09-28 | `6bf9970` | **add: rl** (entire RL module lands in one commit) | **Phase 5 — RL layer** |
| 2026-09-28 | `816a27e` | Spring 2026 course schedule solution + UniTime output updates | |
| 2026-09-28 | `8ddc0db` | add: setup guide upto b1 (`rl/SETUP.md`) | |
| 2026-09-29 | `99100b3` | Merge `dev_riya` into `dev_mihir` | **Phase 6 — curriculum fixes** |
| 2026-09-29 | `df4b55c` | Fix DE/OE elective logic and curriculum structure | |
| 2026-09-29 | `ff16db7` | Restrict OE block to only SY classes | |
| 2026-09-29 | `f521322` | Remove online rooms from generation, disable blocking them | |
| 2026-09-29 | `4db2310` | Add OE-BLOCK and OE enrollments for SY | |
| 2026-09-29 | `694d4ee` | automatic ZIP archive generation for UniTime import | |
| 2026-10-01 | `464435c` | compile project classes and update source files | |
| 2026-10-08 | `222f849` | **gen_students changed to add student_groups** | **Phase 7 — enrollment-derived groups** |

Uncommitted at time of writing: `scripts/zip_0gen_all.py` (new), solver-flag edits to 8 solver XMLs,
`rl/config/unitime-coep-default.properties`, `unitime-out/solver_parameters_recommended.txt`.

---

## 3. Entry points

| Command | Effect |
|---|---|
| `python scripts/gen_all.py [--term Spr12] [--sql ...] [--snapshot 263]` | Runs all 8 generators in dependency order → 16 XML files in `unitime-out/`, then `validate_xmls.py`, `validate_course_offering.py`, `verify_time_patterns.py`, then zips the 16 files (flat, `arcname=name`) to `unitime-out/0gen_all.zip` |
| `python scripts/zip_0gen_all.py --term Spr12` | Retargets the term in every XML of `unitime-out/0gen_all/` and rezips (does **not** regenerate from SQL) |
| `python scripts/eval_timetable_kpis.py --csv <csv> --data-dir <dir> --out <json>` | CSV mode — joins class times to an enrollment XML |
| `python scripts/eval_timetable_kpis.py --xml <solver.xml>` | XML mode — scores the `<students>` block inside a CPSolver solution |
| `python scripts/import_unitime.py` | Pushes the 16 files through the Data Exchange API in order |
| `java -jar rl/target/unitime-rl-*-all.jar --arm B0 --input ... --out ...` | `HeadlessSolve` bake-off runner |
| `rl/run_pipeline.sh` | Steps 2–6 of the RL pipeline end to end |
| UniTime → Administration → Utilities → Scripts | `setup_lunch_breaks.py`, `purge_uploaded_data.py` (Jython, run server-side) |

---

## 4. What each script does

### Data pipeline (Taasika → UniTime)

| Script | LOC | Role |
|---|---|---|
| `taasika_loader.py` | 212 | Parses the MySQL dump textually (no DB server). Prefers `taasika-db/taasika3.sql`, falls back to `taasika2-foss-26jan26.sql`. Default snapshot **240**; `set_global_config()` overrides it. |
| `classifications.py` | 277 | Domain rules mapping Taasika rows → UniTime academic area / classification / major; `find_course_pairs()` does the Lec+Lab merge. |
| `intake.py` | 106 | **Hand-confirmed institutional headcounts.** `N_CSE` = FY 300, SY/TY/BT 200; `N_AIML` = FY 100, else 0; `N_DIVISIONS=2`; `MDM_BLOCK_SEATS=600`; `OE_BLOCK_SEATS=200`; DE2/DE4 = 3 options each. |
| `gen_session_setup.py` | 310 | File 1: session, departments, subject areas, solver groups, date/time patterns, exam periods. |
| `gen_academic.py` | 139 | Files 2–6. `_student_groups` writes `6studentGroup.xml`: one group per Taasika `class` and per `batch`, code = Taasika short name. |
| `gen_buildings.py` | 253 | Files 7–9. Heuristic building inference from room names; travel times. |
| `gen_staff.py` | 107 | File 10. `positionType` from each teacher's `minHrs`/`maxHrs` envelope. |
| `gen_course_catalog.py` | 230 | File 11 + `subject_index.json`. Indian credit formula `1 cr/lec hr + 0.5 cr/lab hr`. |
| `gen_course_offering.py` | 756 | File 12 + `offering_index.json` (`class_limits`, `class_notes`, `lec_to_lab`, `section_offsets`). One `<class type="Lec">` per Taasika `subjectClassTeacher`, one `<class type="Lab">` per `subjectBatchTeacher`. Times deliberately left blank. |
| `gen_preferences.py` | 592 | File 13 — **required**, otherwise UniTime treats classes as "arrange hours" and loads ~0 variables. Time pattern per subpart from minutes/week; `FIXED_ENTRIES_MAP` encodes the institution-specific time blocks (below). |
| `gen_students.py` | 634 | Files 14–16 + `solutions/enrollment_sim_summary.json`. Simulates students, course requests and section enrollments; since `222f849` also emits `<studentGroups>` derived from enrollments. |

### Validation / evaluation

| Script | LOC | Role |
|---|---|---|
| `validate_xmls.py` | 34 | Well-formedness of every generated XML. |
| `validate_course_offering.py` | 66 | Structural check of file 12 before import. |
| `verify_time_patterns.py` | 195 | Taasika subject durations vs. the patterns emitted in file 13. |
| `eval_timetable_kpis.py` | 1044 | **The KPI engine.** CSV mode and XML mode; 10 hard checks, 3 preference checks, efficiency metrics. |
| `relabel_timetable_csv.py` | 230 | Rewrites numeric course numbers (`CS 102`) to Taasika short codes (`CS CN`). |
| `generate_timetable_html.py` | 339 | HTML week-grid viewer. |
| `convert_xml_to_csv.py` | 149 | Solver XML → CSV. |
| `gen_course_type_report.py` | 378 | Regenerates `solutions/course_type_report.md`. |
| `inspect_snap.py` | 94 | Human-readable snapshot dump (produces `compare/*.txt`). |
| `find_pairs.py` | 53 | Lists Lec+Lab/Tut pairing candidates. |

### Server-side Jython (run inside UniTime)

| Script | LOC | Role |
|---|---|---|
| `unitime_scripts/setup_lunch_breaks.py` | 141 | Configures 1-hour dynamic student and instructor lunch breaks between 11:30 and 15:30 via solver criteria; repairs null `SolverType` fields. |
| `unitime_scripts/purge_uploaded_data.py` | 395 | Deletes imported data by step number (`"16"`, `"12, 13"`, `"14-16"`) in reverse dependency order. |

---

## 5. Current dataset — `unitime-out/0gen_all/` **[verified]**

Term attribute in every file: `Spr122026` (academic term `Spr12`, year `2026`).

| # | File | Bytes | Root element | Contents |
|---|---|---|---|---|
| 1 | `1sessionSetup.xml` | 12,486 | `sessionSetup` | session, depts, subject areas, date/time patterns |
| 2 | `2academicArea.xml` | 496 | `academicAreas` | 2 areas (BT, MT) |
| 3 | `3academicClassification.xml` | 786 | `academicClassifications` | 5 (FY, SY, TY, BT, MT) |
| 4 | `4Major.xml` | 1,832 | `posMajors` | 15 majors |
| 5 | `5Minor.xml` | 374 | `posMinors` | 0 (empty stub by design) |
| 6 | `6studentGroup.xml` | 25,485 | `studentGroups` | **242 groups** |
| 7 | `7buildingRoomImport.xml` | 21,604 | `buildingsRooms` | **6 buildings, 42 rooms** |
| 8 | `8roomSharing.xml` | 9,916 | `roomSharing` | 45 blocks |
| 9 | `9travelTimes.xml` | 2,722 | `traveltimes` | 7 blocks |
| 10 | `10staff.xml` | 19,618 | `staff` | **115 instructors** |
| 11 | `11courseCatalog.xml` | 44,081 | `courseCatalog` | **158 courses** |
| 12 | `12courseOffering.xml` | 100,340 | `offerings` | **56 offerings, 84 subparts, 291 classes** |
| 13 | `13preferences.xml` | 95,146 | `preferences` | 362 preference blocks |
| 14 | `14studentInfo.xml` | 657,518 | `students` | **1,130 students, 5,767 group references** |
| 15 | `15studentRequest.xml` | 495,638 | `request` | 1,130 students |
| 16 | `16studentenrollments.xml` | 661,230 | `studentEnrollments` | 1,130 students, **9,148 class enrollments** |

Student population **[file: `solutions/enrollment_sim_summary.json`]**:
B.Tech 1,000 (FY 400 = 300 CSE + 100 AIML; SY 200; TY 200; BT 200) + M.Tech 130 = **1,130**.
ID format `61yy03aaa`, `yy` ∈ {01=FY … 05=MT}.
Known overflow: `CS PPS-FY Lec` 200 unplaced, `MT PSEC2-EAI Lab` 2 unplaced.

Source: Taasika snapshot **263** `Published-13july26-v2` from `taasika-db/taasika3.sql`
(`compare/263.txt`; the earlier dataset documented in `unitime-out/README.md` used snapshot 240
from `taasika2-foss-26jan26.sql`).

---

## 6. Institution-specific constraints

### Time blocks — `gen_preferences.py: FIXED_ENTRIES_MAP`

| Rule | Courses | Days | Window | Level |
|---|---|---|---|---|
| `MDM_Required` | `MDM*` | Mon, Tue | 16:30–18:30 | Required |
| `OE_Required` | `OE*` | Mon, Tue | 09:30–10:30 | Required |
| `Non_MDM_Prohibited` | `*` except `MDM*`, `OE*` | Mon, Tue | 16:30–18:30 | Prohibited |
| `SY_Non_OE_Prohibited` | CO, CoI, DTL, DTL-Lab, Eco, OOPD, OOPD-Lab, TOC, TOC-Tut | Mon, Tue | 09:30–10:30 | Prohibited |

First matching rule wins. `R`/`1`/`0`/`2` levels mark the one slot that matches the exact day set and
fits the window; `P` marks every candidate slot that overlaps the days *and* the window.

### Time patterns — `_time_pattern(sp_type, min_per_week)`

Lectures: 240 → `2 x 120`, 180 → `3 x 60`, 120 → `2 x 60`, else `n x 60`.
Lab/Rec: 480 → `1 x 480 Project`, 180 → `1 x 180`, 120 → `1 x 120`, 60 → `1 x 60`. Fallback `Exact Time`.

### Lunch break
Not a time-pattern exclusion: a *dynamic* 1-hour window between 11:30 and 15:30 for students and
instructors, installed as solver criteria by the Jython script `setup_lunch_breaks.py`.
Rooms stay available all weekday.

### Group membership (new in `222f849`)
Group code = the class's `scheduleNote` from `12courseOffering.xml`, also stored as `class_notes` in
`scripts/offering_index.json` (**289 entries [verified]**, e.g. `CS|CoI|Lec|1 → SY-Div1`,
`CS|AI|Lab|1 → TY1-T1`). `gen_students.py` emits `<studentGroups><studentGroup group="CODE"/></studentGroups>`
inside each `<student>`, one entry per enrolled class, filtered against the codes declared in
`6studentGroup.xml`.

---

## 7. Solver configuration — `rl/config/unitime-coep-default.properties`

Exported from the pilot's UniTime instance. Notable values:

```
Basic.Mode=Initial                        Basic.DisobeyHard=false
Comparator.Class=...coursett.heuristics.TimetableComparator
Comparator.StudentConflictWeight=0.2      Comparator.HardStudentConflictWeight=0.8
Comparator.DistStudentConflictWeight=0.2  Comparator.RoomPreferenceWeight=1.0
Comparator.TimePreferenceWeight=0.3       Comparator.TooBigRoomWeight=0.1
Construction.Class=...NeighbourSelectionWithSuggestions
Extensions.Classes=org.cpsolver.ifs.extension.ConflictStatistics   General.CBS=true
General.CompleteSolutionFixInterval=-1    General.IncompleteSolutionFixInterval=-1
General.AutoSameStudents=true             General.AutoSameStudentsConstraint=SAME_STUDENTS
Data.Initiative=COEP                      Data.Term=2026Spr
Curriculum.StudentCourseDemadsClass=Projected Student Course Demands
```

Three settings were changed during this semester to make the solver honour the imported
enrollments instead of re-sectioning students (edits applied to this file, to
`unitime-out/solver_parameters_recommended.txt`, and to 8 solver XMLs):

1. Student Course Demands → **Enrolled Student Course Demands** (UI setting; the committed file
   still reads `Projected Student Course Demands` — see `DISCREPANCIES.md`).
2. `General.SwitchStudents=false`
3. `Global.LoadStudentEnrlsFromSolution=true`

---

## 8. The RL layer

Maven module `unitime-rl` 0.1.0-SNAPSHOT, `maven.compiler.release=17`.
Dependencies: cpsolver `1.4-SNAPSHOT` (local; `1.4.94` from Maven Central is a documented
substitute), gRPC 1.84.0, protobuf 4.36.2, ONNX Runtime 1.30.0, log4j 2.25.4, dom4j 2.1.5,
JUnit Jupiter 5.11.4.

25 Java classes (largest: `RlNeighbourSelection` 24 KB, `HeadlessSolve` 18 KB,
`SolverEnvironment` 14 KB, `SearchMetrics` 13 KB, `ConflictOracle` 11 KB).

**Design invariant:** nothing in the module writes a placement. Every move is produced by a stock
CPSolver generator and accepted or rejected by CPSolver's Great Deluge, so hard constraints are as
safe as in a normal solve.

### Eight operators (`Operators.java`)
0 `TIME_CHANGE`, 1 `ROOM_CHANGE`, 2 `TIME_AND_ROOM`, 3 `LECTURE_SWAP`, 4 `SUGGESTION`,
5 `STUDENT_SWAP`, 6 `BIASED_TIME_CHANGE`, 7 `BIASED_STUDENT_SWAP`.
Operator 4 is masked while the solution is complete (Suggestion only repairs unassigned classes);
5 and 7 are masked while no class has an alternative section.

### 48-dimensional state (`StateEncoder.DIM = 48`, `NAMES` verbatim)
`student_violation_rate, pair_violation_rate, intensity, concentration, slot_bin_0..9,
improvement_gap, recent_slope, assigned_ratio, unassigned_fraction, hard_violations, norm_total,
norm_time_pref, norm_room_pref, norm_dist_pref, norm_student_conflict, room_util_mean,
room_util_max, room_util_std, instr_util_mean, instr_util_max, progress, acceptance_rate,
idle_fraction, null_fraction, prev_op_0..7, churn, lectures_in_conflict_share,
pairs_per_conflicted_student, norm_too_big_rooms, norm_useless_half_hours, norm_back_to_back,
norm_broken_time_patterns`

### Reward
`Phi = -C - 0.5 U - 5 H - 0.05 O`, step reward = potential difference of the incumbent, minus
`1e-4` per macro-step. Defaults `Rl.K=50` solver iterations per macro-step.

### Arms
| Arm | Selector | Comparator |
|---|---|---|
| B0 | `FixCompleteSolutionNeighbourSelection`, stock weights | native (`TimetableComparator`) |
| B1 | same, `--student-conflict-weight W` (moves `Comparator.`, `Lecture.` and `Placement.NrStudConfsWeight2` together) | native |
| B2 | `SimpleSearch` Great Deluge + `RandomStudentSwap` + `Suggestion@0.01` | native |
| L | `RlNeighbourSelection` + LinUCB over the 8 operators | lexicographic |
| R | `RlNeighbourSelection` + frozen ONNX policy | lexicographic |
| SHADOW | default selector executes, policy only logged | native |

LinUCB is a disjoint linear contextual bandit (online, linear — not a neural network).

### Trained artifacts
`models/bc_policy.pt` (100 KB), `models/bc_policy.onnx`, `models/policy.onnx` (96 KB),
`models/ppo/maskable_ppo.zip` (590 KB).
`models/ppo/train_args.json` **[file]**: 3 gRPC workers (`localhost:50051-53`), instance `spr2026`,
BC init from `models/bc_policy.pt`, **100,000 timesteps**, `n_steps=256`, `batch_size=256`,
`lr=3e-4`, `ent_coef=0.01`, `gamma=1.0`, `gae_lambda=0.95`, `max_assigned_drop=0.05`, `seed=0`.
A separate `models/ppo_smoke/` holds a 4,000-timestep synthetic smoke run.

---

## 9. Results and artifacts

### 9.1 The B1 weight sweep — the decisive experiment

`rl/runs/sweep/`, instance `rl/instances/spr2026.xml` (Spr6 export, 262 classes, 990 students),
900 s wall-clock per run, 3 seeds per weight, arm B1, reference arm B0.

`summary.md` **[file]**:

| weight | C (median) | assigned | soft | n |
|---|---|---|---|---|
| 0.2 | 0.0343 | 1 | 62 | 3 |
| 0.5 | 0.0192 | 1 | 66 | 3 |
| 1 | 0.0263 | 1 | 67 | 3 |
| 2 | 0.0030 | 1 | 65 | 3 |
| **5** | **0** | 1 | 69 | 3 |
| 10 | 0.0040 | 1 | 64 | 3 |

> `spr2026: chosen weight = 5 (C=0.0000, assigned=1.0000); reduction vs B0 = 1.000 ->
> B1 ALONE CLEARS 25%: research question answered in the negative, RL run optional`

B0 reference **[verified]**: C per seed = 0.0414, 0.0263, 0.0515 → median **0.0414** (41/990).
Initial C of the loaded instance, identical for every run: **0.5313** (526/990).

Recomputing the medians from the per-seed `metrics.json` files on disk reproduces every row
**except weight 5** — see `DISCREPANCIES.md` §1. The conclusion is unaffected: the best weight is
either 5 (C = 0) or 2 (C = 0.0030), and both clear the 25 % bar against B0's 0.0414.

### 9.2 Bake-off `rl/runs/bakeoff-spr2026_10m_w5/` — **not usable as evidence**

Arms B0, B1, B2 × 10 seeds × 900 s on `spr2026_10m_w5.xml`. Every arm reports
`C_median = 0`, `assigned = 1`, `hard = 0`. The per-seed `metrics.json` shows
`initial.student_violation_rate = 0.0` — the instance was already conflict-free when loaded, so the
run measures nothing about conflict reduction. Arms L and R were never run on it
(`## Relative reduction of R versus B1` is empty: "(arms B1 and/or R missing)").

Useful secondary numbers from it **[file]**: B0 2,483 committed neighbourhoods vs B2 3.09 M
(overhead ratio 0.001), soft penalty B0/B1 25 vs B2 15, `too_big_rooms` 333 vs 362.

### 9.3 KPI reports in `solutions/` **[file]**

CSV mode (joined against the then-current `unitime-out/`, 1,290 simulated students):

| Report | Source CSV | Classes | Hard feas. | Pref. | Students conflicted | Pairs |
|---|---|---|---|---|---|---|
| `kpi_report.json` | `COEPSpr62026_v2.csv` | 260/261 | 94.98 | 25.20 | 587 / 1290 | 1,485 |
| `kpi_report_2785.json` | `COEPSpr2026_v3_2785.csv` | 262/260 | 92.66 | 23.78 | 507 / 1290 | 895 |
| `kpi_weight5_report.json` | `course-solution_weight5.csv` | 262/260 | 90.97 | 25.00 | **676 / 1290** | 1,076 |
| `kpi_weight20_report.json` | `course-solution_weight20.csv` | 262/260 | 88.96 | 24.19 | **894 / 1290** | 2,126 |
| `kpi_scw_v4_report.json` | `COEPSpr2026_v4.csv` | 262/260 | 88.96 | 24.19 | 894 / 1290 | 2,126 |
| `kpi_report_MacMini_v1.json` | `MacMini_v1.csv` | 254 | 87.40 | 100.0 | 0 / 2130 | 0 |

XML mode (scores the `<students>` block inside a CPSolver solution):

| Report | Instance | Classes | Students | Conflicted | Rate | Hard feas. |
|---|---|---|---|---|---|---|
| `spr2026.kpi.json` | `rl/instances/spr2026.xml` (Spr6 export) | 262 | 990 | **526** | 0.5313 | 92.15 |
| `spr2026_mihir.kpi.json` | `spr2026_mihir.xml` | 262 | 990 | 0 | 0 | 97.67 |
| `spr2026_10m_w5.kpi.json` | `spr2026_10m_w5.xml` | 262 | 990 | 0 | 0 | 98.26 |
| `solution.kpi.json` | `rl/runs/sweep/w5/spr2026/B1/seed1/solution.xml` | 262 | 990 | **26** | 0.0263 | 97.42 |
| `spr2026_10_LE_SS_Enrolled.kpi.json` | pinned Spr10 run | 290 | 1,130 | **32** | 0.0283 | 97.77 |
| `spr2026_10_LE_90m_w5.kpi.json` | Spr10, 90 min, w=5 | 290 | **0** | 0 | 0 | 97.55 |

**Cross-validation worth reporting:** `solution.kpi.json` (Python evaluator, 26/990, 0.026263) and
the Java `ConflictOracle` in `rl/runs/sweep/w5/.../metrics.json` (0.026262626) agree exactly on the
same solution file — two independent implementations of the conflict rule.

### 9.4 Headline result of the semester — **[verified, reproduced during this exploration]**

```
python scripts/eval_timetable_kpis.py --csv unitime-out/spr2026_11_all_flags.csv \
       --data-dir unitime-out/0gen_all
```

| Metric | Value |
|---|---|
| Classes in offerings / in solution | 291 / 291 |
| Coverage | 290 / 291 (1 unassigned) |
| Hard feasibility score | **98.85** |
| Hard checks / failures | 4,341 / 105 |
| Time-pattern fidelity | 290/290 (100 %) |
| Date pattern | 290/290 (100 %) |
| Room capacity | 290/290 (100 %) |
| Lunch/weekend | 290/290 (100 %) |
| Instructor double-booking | 291/291 (0 conflicts) |
| Room double-booking | 291/291 (0 conflicts) |
| **Student conflicts** | **40 / 1,130 students (96.46 % clean), 40 pairs** |
| Student lunch breaks | 1,067/1,130 (63 violations) |
| Instructor lunch breaks | 47/48 (1 violation) |
| Travel violations | 0 |
| Back-to-back | 31.96 % |
| Preference score | 6.29 (room preference 12.59 %, instructor identity 0.0 %) |
| Rooms indexed / staff | 42 / 115 |

All 40 conflicts are first-year: `CS PPS-FY Lab` vs `CS FY-Reserve Lec`
(Lab 1 × Reserve Lec 3 Tue, Lab 2 × Reserve Lec 3 Fri, Lab 7 × Reserve Lec 2 Wed,
Lab 9 × Reserve Lec 1/2 Fri).

> The `instructor_identity` 0.0 % is a **name-format artifact**, not a scheduling failure: the
> evaluator compares `"Joshi, A"` (Taasika, `General.InstructorFormat=last-initial`) against
> `"Amit Joshi"` (UniTime export). It must be reported as an evaluator limitation.

---

## 10. Conflict rule (used identically by the engine, the Java oracle and the Python evaluator)

Two classes conflict for a student iff they **share a day bit** AND their **slot intervals overlap**
(touching endpoints do not count) AND, if both carry date patterns, they **share a week bit**.
Room and instructor are irrelevant. Days are a 7-character binary string, index 0 = Monday.
Slots are 5 minutes when `slotsPerDay = 288`.

`scripts/sectioning_slot_conflicts.py` keys on an exact `day start-end` string and therefore misses
partial overlaps — it reports 0 where real overlaps exist. Do not cite it.

---

## 11. Known open issues in the codebase

- `resolve_btech` dead code in `gen_students.py` (fixed upstream in `464435c`).
- `PSEC2-EAI Lab` over-subscribed by 2 students; `CS PPS-FY Lec` 200 unplaced.
- `BT-Div1`, `BT-Div2`, and `FY-PP1-A_` groups have zero members.
- The 40 first-year conflicts are unresolved. Two options were identified: retime the four labs, or
  add required `DIFF_TIME` distribution constraints.
- `12courseOffering.xml` carries `CS PP-FY Lab 16..41` which are no longer wanted; removing them
  requires re-importing file 12 (incremental import still runs `deleteUnmatchedClasses`) after
  uncommitting any saved solution.

---

## 12. Operational knowledge (hard-won, belongs in the report)

- **Term code** = academic term + year, e.g. `Spr122026` — not `2026Spr12`.
- Import order is the numbered 1→16 sequence; each file references entities from earlier ones.
- Buildings imported by file 7 are **global**, not session-scoped. After import you must run
  **Administration → Academic Sessions → Buildings → Update Data**, otherwise every class reports
  *"has no available room (class not loaded)"*.
- Instructors need **Courses → Input Data → Instructors → Manage Instructor List** before they
  attach to classes.
- The zip for Data Exchange must have the 16 XML files at the **zip root** (`arcname=path.name`);
  `zip -r 0gen_all.zip 0gen_all` nests them in a folder and fails.
- Without `13preferences.xml`, UniTime treats classes as "arrange hours" and loads ~0 variables.
- `BaseCourseOfferingImport` with `incremental="true"` skips
  `deleteUnmatchedInstructionalOfferings` / `deleteUnmatchedCourseOfferings` but **still** runs
  `deleteUnmatchedClasses` for offerings present in the file.
- The solver model XML (`<timetable version="2.5">`) is **not** produced by Data Exchange; it comes
  from the solver screen's *Export XML* button. Set
  `unitime.solution.export.names=true` first, otherwise the export is anonymised.
- With *Projected Student Course Demands* and no last-like data, the solver loads **zero students**
  and silently reports `Student conflicts: 0`.

---

## 13. Software stack

| Component | Version | Where it is used | Source |
|---|---|---|---|
| Java | **21** | UniTime web application under Tomcat | Sem VI report §4 |
| Java | **17** (`maven.compiler.release=17`, "JDK 17+") | `rl/` Maven module, `HeadlessSolve`, `EnvServer` | `rl/pom.xml`, `rl/README.md`, `rl/SETUP.md` |
| MySQL | 8.4 | UniTime backend | Sem VI report §4 |
| Apache Tomcat | 9.0 | servlet container | Sem VI report §4 |
| Maven | 3.9+ | builds `unitime-rl` | `rl/SETUP.md` |
| Python | 3.10+ | pipeline scripts, `unitime_rl` | `rl/SETUP.md` |
| CPSolver | 1.4-SNAPSHOT (local) / 1.4.94 (Central) | solver library | `rl/pom.xml`, `rl/SETUP.md` |
| gRPC / protobuf | 1.84.0 / 4.36.2 | training environment transport | `rl/pom.xml` |
| ONNX Runtime | 1.30.0 | in-JVM frozen policy | `rl/pom.xml` |

These are **not** in conflict: Java 21 runs the UniTime server, Java 17 is the compile target of the
RL module (which requires JDK 17 or newer, so it also builds and runs on 21).

---

## 14. Evidence gaps — must be `\todo{}` or omitted in the report

1. **No RL arm (L or R) has been run on a real COEP instance.** The only L/R numbers in the repo are
   on the 120-class synthetic instance in `rl/README.md`, explicitly labelled "only a pipeline
   check, not evidence for the hypothesis".
2. **No held-out term.** Only Spr6-derived instances exist; `run_pipeline.sh` warns that passing the
   same file as `--train` and `--heldout` makes the result in-sample only.
3. `rl/runs/` contains no `bakeoff` directory with arms L/R, no `shadow/` trajectories, and no
   `models/ppo/discarded_episodes.jsonl`.
4. The four root-level PNG screenshots have not been identified; caption them only after opening.
5. No wall-clock timing for the full `gen_all.py` pipeline has been recorded.
6. The deck's "weight 5 → 614 student conflicts" does not match any committed artifact
   (`kpi_weight5_report.json` says 676). See `DISCREPANCIES.md` §4.
