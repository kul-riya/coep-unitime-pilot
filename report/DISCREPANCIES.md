# DISCREPANCIES.md — conflicts between the repository, the deck and the Semester VI report

Resolution rule given in the task: **the repository wins**; the deck supplies candidates that must be
verified; the Semester VI PDF supplies structure and still-valid background, not current facts.

Legend for "Resolution":
**R** = repo value adopted · **D** = deck value confirmed by the repo · **B** = both correct, different scope.

---

## 1. Weight-5 row of the B1 sweep: `summary.md` disagrees with the per-seed `metrics.json`

| Source | Weight 5, median C over 3 seeds |
|---|---|
| `rl/runs/sweep/summary.md` and `sweep_results.csv` | **0.0000** (per-seed 0.0, 0.0, 0.0444) |
| Per-seed `rl/runs/sweep/w5/spr2026/B1/seed*/metrics.json` recomputed today | **0.0263** (per-seed 0.0263, 0.0, 0.0444) |

Only seed 1 differs: the CSV records iterations 2,545 / C = 0.0, the `metrics.json` on disk records
iterations 2,526 / C = 0.0263. Every other weight reproduces exactly. The `metrics.json` of seed 1
is corroborated by `solutions/solution.kpi.json`, which scores
`rl/runs/sweep/w5/spr2026/B1/seed1/solution.xml` at 26/990 = 0.026263 with the independent Python
evaluator.

**Diagnosis.** `bakeoff.run_one` skips any job whose `metrics.json` already exists, so re-running the
sweep with `--save-solution` (as `rl/SETUP.md` §5 instructs) after deleting that one directory
replaced seed 1's `metrics.json` and `solution.xml` with a fresh run, while `summary.md` and
`sweep_results.csv` kept the original aggregation. All file mtimes are identical (git checkout), so
timestamps cannot order the events.

**Resolution (R).** Report the committed `summary.md` table as the recorded experiment, and state in
a footnote that recomputing from the per-seed files gives weight 2 (C = 0.0030) rather than weight 5
(C = 0) as the minimum. **The conclusion is unaffected:** against B0's median C = 0.0414, the best
weight gives a relative reduction of 1.000 (weight 5) or 0.927 (weight 2), and both clear the
pre-registered 25 % bar. Do **not** present "C = 0 at weight 5" as a clean single-point result.

---

## 2. Java version: 21 (Semester VI report) vs 17 (deck)

| Claim | Source |
|---|---|
| Java 21 | Sem VI report §4; deck slide 4 |
| Java 17 | deck (pipeline/RL side) |
| `maven.compiler.release=17`; "JDK 17+" | `rl/pom.xml` line 18; `rl/README.md` "Build"; `rl/SETUP.md` §0 |

**Resolution (B).** Not a conflict — two different components.
**Java 21** is the runtime for the UniTime web application on Tomcat 9.0 with MySQL 8.4.
**Java 17** is the *compile target* (`maven.compiler.release=17`) of the `unitime-rl` Maven module;
both `rl/README.md` and `rl/SETUP.md` state the requirement as "JDK 17+", so the module also builds
and runs on 21. The report must say exactly this rather than picking one number.

---

## 3. Student counts: 1,130 vs 1,290 vs 2,130 vs 990

| Count | Where | What it is |
|---|---|---|
| **2,130** | `unitime-out/README.md` §14; `kpi_report_MacMini_v1.json` | the original simulation: 500/year × FY–BT + 130 MT |
| **1,290** | `kpi_report.json`, `kpi_weight5/20_report.json`, `kpi_scw_v4_report.json` | the Spr6-era simulation (B.Tech 1,160 + MT 130) |
| **990** | `rl/instances/spr2026.xml`, all `rl/runs/*` | students that actually carry enrollments in the Spr6 UniTime export |
| **1,130** | `unitime-out/0gen_all/14studentInfo.xml` **[verified]**; `solutions/enrollment_sim_summary.json` | the **current** dataset: FY 400 + SY 200 + TY 200 + BT 200 + MT 130 |

**Resolution (R).** 1,130 is the current figure and the one the report headlines. The others are
historical and must always be labelled with their instance. The 1,290 vs 990 gap is **not** attrition:
1,290 was the full simulated roll of the Spr6-era `unitime-out/`, while 990 is the subset that the
UniTime export carried enrollments for. Mixing them changes the denominator of every conflict rate —
which is exactly the reconciliation the deck asks for (see §6).

---

## 4. Weight experiment: deck says 614 conflicts at weight 5; the repo says 676

| Weight | Deck | Repo artifact |
|---|---|---|
| 5 | 614 students | **676 / 1,290** — `solutions/kpi_weight5_report.json` (1,076 pairs) |
| 20 | 894 students | **894 / 1,290** — `solutions/kpi_weight20_report.json` (2,126 pairs) ✔ |

The weight-20 figure matches exactly; the weight-5 figure does not, and no committed artifact
produces 614. A third file, `kpi_scw_v4_report.json` (`COEPSpr2026_v4.csv`), is byte-identical in its
summary to the weight-20 report (894 / 2,126), so `COEPSpr2026_v4.csv` and
`course-solution_weight20.csv` are the same solution under two names.

**Resolution (R).** Quote **676** for weight 5 and 894 for weight 20, both from the named JSON files,
and record that the deck's 614 is unsourced. Add the caveat the deck itself flags: these CSV-mode
counts were joined against the **then-current** `unitime-out/` enrollments (1,290 students, 262
classes), not the current dataset, so they measure the old instance.

Independently, these numbers must not be read as "a higher weight is worse". The CSV-mode join
re-derives student–class membership from a *different* enrollment file than the one the solver used,
so the two runs are not a controlled comparison. The controlled comparison is the headless sweep
(§1), which holds the instance fixed and shows C falling from 0.0414 to 0.003–0.0 as the weight rises.

---

## 5. Offerings and classes: 54 vs 58 vs 56; 262 vs 291

| Figure | Source |
|---|---|
| 63 → 54 offerings (v5 pairing fix) | deck version history (first version of the list) |
| 63 → 58 offerings | deck version history (corrected in chat); `solutions/HANDOFF.md` says v5 = 58 offerings / 244 classes |
| 58 offerings | `unitime-out/README.md` §12 |
| **56 offerings, 291 classes, 84 subparts** | `unitime-out/0gen_all/12courseOffering.xml` **[verified]** |
| 54 offerings, 262 classes | deck "Spr6 export" |
| 262 classes | `rl/instances/spr2026.xml`, all `rl/runs/*`, `spr2026*.kpi.json` |
| 260 / 261 / 254 classes | older CSV-mode KPI reports |
| 290 classes | `spr2026_10_LE_SS_Enrolled.kpi.json`, `spr2026_10_LE_90m_w5.kpi.json` (Spr10) |

**Resolution (R).** The current dataset is **56 offerings / 291 classes**. The 58/244 figure in
`HANDOFF.md` and the 58 in `unitime-out/README.md` describe the earlier snapshot-240 dataset and are
superseded. Use "63 → 58" for the v5 pairing fix (sourced to `HANDOFF.md`), not "63 → 54".
Every class count in the report must name its instance; a table of instances (§9.3 of `REPO_NOTES.md`)
is the clean way to do it.

---

## 6. Conflict rate: 53.1 % (solver checker) vs 45.5 % (KPI evaluator)

Both are in the repo and both are correct — they measure different things.

| | Solver checker (Java `ConflictOracle`) | KPI evaluator (Python, CSV mode) |
|---|---|---|
| Value | 526 / 990 = **0.5313** | 587 / 1,290 = **45.5 %** conflicted (54.5 % pass) |
| Source | `rl/runs/sweep/*/metrics.json` `initial.student_violation_rate`; `solutions/spr2026.kpi.json` | `solutions/kpi_report.json` |
| Instance | `rl/instances/spr2026.xml` (Spr6 solver export) | `COEPSpr62026_v2.csv` joined to the Spr6-era `unitime-out/` |
| Denominator | students with ≥ 2 assigned classes in the solver model (990) | all simulated students in the enrollment XML (1,290) |
| Membership | the `<students>` block *inside* the solver file | re-derived by joining the CSV to `16studentenrollments.xml` |

**Resolution (B).** Report both, with their denominators, as an illustration of why the evaluation
framework had to be pinned down. Two further points belong with them:

- The two tools are **not** inconsistent where they can be compared directly. On the same file
  `rl/runs/sweep/w5/spr2026/B1/seed1/solution.xml`, the Java oracle reports 0.026262626 and the
  Python evaluator reports 0.026263 (26/990) — exact agreement. The divergence above is entirely
  due to instance and denominator, not to the conflict rule.
- The conflict rule itself is identical in both: same day bit **and** overlapping slot intervals
  (touching endpoints excluded) **and**, if both classes carry date patterns, a shared week bit.

---

## 7. The "0 conflicts" results are artefacts, not improvements

Four artifacts report 0 student conflicts:

| Artifact | Why it is 0 |
|---|---|
| `solutions/spr2026_mihir.kpi.json`, `spr2026_10m_w5.kpi.json` | students were re-sectioned (`SwitchStudents` / initial sectioning moved students between lab sections); the deck notes 33 overlapping lab enrollments were bypassed |
| `rl/runs/bakeoff-spr2026_10m_w5/` (all 10 seeds × 3 arms) | `initial.student_violation_rate = 0.0` — the instance was already conflict-free on load, so the 900 s run measured nothing |
| `solutions/spr2026_10_LE_90m_w5.kpi.json` | `enrolled_students: 0`, `students_total: 0` — **no students were loaded at all**; the rate is 0/0 |
| `kpi_report_MacMini_v1.json` | 0 / 2,130, but only 254 classes and 2 instructor conflicts; a different, earlier instance |

**Resolution (R).** None of these may be presented as a conflict-reduction result. The report must
state the mechanism in each case. The honest counterpart is §8.

---

## 8. "Real pin: 32, then 40" — confirmed

| Figure | Source | Status |
|---|---|---|
| 32 / 1,130 (0.0283) | `solutions/spr2026_10_LE_SS_Enrolled.kpi.json`, 290 classes, term Spr10 | **[file]** confirmed |
| **40 / 1,130 (3.54 %)** | `unitime-out/spr2026_11_all_flags.csv` scored against `unitime-out/0gen_all` | **[verified — reproduced during exploration]** |

**Resolution (D, confirmed).** These are the real pinned-enrollment results, obtained with
*Enrolled Student Course Demands* + `General.SwitchStudents=false` +
`Global.LoadStudentEnrlsFromSolution=true`. They are higher than the "0 conflicts" numbers precisely
because students can no longer be silently moved. The 40 are all first-year
`CS PPS-FY Lab` × `CS FY-Reserve Lec` overlaps. This is the headline result of the semester.

---

## 9. Source snapshot of the current dataset: 240 (XML header) vs 263 (commit) vs 242 (evidence)

| Claim | Source |
|---|---|
| snapshot 240 `published-19jan26` | `created=` attribute of 4 files in `0gen_all`; `unitime-out/README.md` |
| snapshot 263 `Published-13july26-v2` | commit `942c24d` "integrate snapshot 263 data" |
| **snapshot 242 `published-v4-26jan26`** | arithmetic below |

The `created="Generated from Taasika snapshot 240"` string is **hard-coded** in `gen_session_setup.py`,
`gen_buildings.py` and `gen_course_offering.py`, so it is not evidence of anything.

Counting instead **[verified]**:

| Quantity | snap 240 | snap 242 | snap 263 | `0gen_all` |
|---|---|---|---|---|
| classes + batches | 43 + 165 = 208 | **43 + 199 = 242** | 32 + 128 = 160 | **242 groups** ✔ |
| teachers | 113 | **115** | 67 | **115 staff** ✔ |
| rooms | 49 | 49 | 29 | 42 (= 49 − 7 online, commit `f521322`) |

**Resolution (R).** `unitime-out/0gen_all` was generated from **Taasika snapshot 242
(`published-v4-26jan26`) in `taasika-db/taasika3.sql`**. Snapshot 240 is the Semester VI dataset and
is what `unitime-out/README.md` documents; snapshot 263 is a later Odd-Sem-26/27 snapshot that was
integrated into the loader but is not the source of the current files. The report should state 242
and note the stale hard-coded provenance string as a known defect.

---

## 10. Rooms and buildings: 49 rooms / 7 buildings vs 42 rooms / 6 buildings

**Resolution (R).** 49/7 is the Semester VI figure (`unitime-out/README.md` §7) and includes the
virtual `ONL` (Online) building. Commit `f521322` "Remove online rooms from generation and disable
blocking them" dropped it. The current `7buildingRoomImport.xml` has **6 buildings / 42 rooms**
**[verified]**: AC 14, CSED 15, ENTCX 5, NCSE 2, BHAU 2, UNAV 4. The `UNAV` ("Unavailable Lab Pool")
building is retained, which is why 17 of 291 assignments (5.84 %) still land on UNAV rooms.

---

## 11. Instructor counts: 113 vs 115 vs 117

| Count | Source |
|---|---|
| 113 | `unitime-out/README.md` §10; `staff` field of every CSV-mode KPI report |
| 117 instructor records, 46 distinct in timetable | deck "Spr6 export" |
| **115** | `unitime-out/0gen_all/10staff.xml` **[verified]**, = snapshot 242 teacher count |

**Resolution (R).** 115 in the current dataset. The current solution uses **48** distinct instructors
(`instructor load ... n=48` in the verified KPI run), not 46.

---

## 12. Solver configuration file still says *Projected Student Course Demands*

`rl/config/unitime-coep-default.properties` contains
`Curriculum.StudentCourseDemadsClass=Projected Student Course Demands`, but both `rl/README.md` §0
and the semester's pinning work require **Enrolled Student Course Demands**.

**Resolution (R).** Not a contradiction to hide: the properties file is an *export* of the UniTime
configuration taken before the change, and the setting is applied in the UniTime UI
(Administration → Solver → Configurations), not in this file. With *Projected* and no last-like data
the solver loads zero students and silently reports `Student conflicts: 0` — which is the mechanism
behind the 0/0 result in §7. The report should present this as a configuration pitfall that was
diagnosed, and note that the committed file is stale. (The two companion flags,
`General.SwitchStudents=false` and `Global.LoadStudentEnrlsFromSolution=true`, *were* written into
this file and into the 8 solver XMLs.)

---

## 13. Deck claims that the repository confirms exactly

No action needed beyond citing the source.

| Deck claim | Repo evidence |
|---|---|
| 56 offerings, 291 classes, 1,130 students (FY 400, SY/TY/BT 200, MT 130), 115 staff, 6 buildings, 42 rooms, term Spr12 | `unitime-out/0gen_all/*` **[verified]** |
| 526/990 = 53.1 % solver-checker rate | `initial.student_violation_rate = 0.5313` in every `rl/runs/sweep/*/metrics.json`; `solutions/spr2026.kpi.json` |
| 894 conflicts at weight 20 | `solutions/kpi_weight20_report.json` |
| RL = 25 Java classes + 11 Python modules | `find rl/src/main/java -name '*.java'` = **25**; `ls rl/python/unitime_rl/*.py` = **11** **[verified]** |
| Grid 7 days × 10 hourly slots, 08:30–18:30 | `unitime-out/README.md`; time patterns `1 x 60` … `5 x 60`, `1 x 120`, `2 x 120`, `1 x 180`, `1 x 480 Project`, `Exact Time` in `1sessionSetup.xml` **[verified]** |
| Synthetic smoke test: 120 classes, 600 students, 6 rooms, 30 s, one seed | `rl/README.md` "Smoke-test results", which itself says "only a pipeline check, not evidence for the hypothesis" |
| ~100 macro-steps/s/worker, reset < 1 s, ONNX 0.08 ms, torch–ONNX deviation 2e-6 | `rl/README.md`; all from the **synthetic** instance |
| "No claim that RL beats the baselines unless the repo contains evidence" | **The repo contains no such evidence.** See §14. |

---

## 14. The RL hypothesis is untested on real data — the single most important caveat

- `rl/runs/bakeoff-spr2026_10m_w5/summary.md` has arms **B0, B1, B2 only**; the relative-reduction
  section prints "(arms B1 and/or R missing)". Arms **L and R were never run on a COEP instance.**
- The only L/R numbers anywhere are on the 120-class synthetic instance in `rl/README.md`, where all
  arms tie at C = 0.133 and arm R (BC-only ONNX) is *worse* at 0.267 with the policy "collapsed to
  RoomChange".
- PPO was trained for 100,000 timesteps (`rl/models/ppo/train_args.json`) on the single instance
  `spr2026`; no held-out term exists, and `rl/run_pipeline.sh` warns that using the same file for
  `--train` and `--heldout` makes any result in-sample only.
- `rl/runs/` has no shadow-log directory and no `discarded_episodes.jsonl`.

**Resolution (R).** The report must present the RL layer as **implemented and instrumented, with its
research question answered in the negative by the B1 control**: the sweep showed that simply raising
`Comparator.StudentConflictWeight` already clears the pre-registered 25 % improvement bar, so the
learned policy was not needed on this instance. That is a legitimate and publishable finding. Section
11 must be explicit about implemented / measured / hypothesis, and must make no performance claim for
arms L or R.

---

## 15. Version history: deck list vs git

| Deck | Git evidence | Verdict |
|---|---|---|
| v1 Taasika→UniTime | `8586fb6`…`cddefd1` (2026-06-23) | ✔ |
| v2 division-aware enrollments | `3234069` (2026-07-29) "Simulate preference-based student enrollments with `61yy03aaa` IDs" | ✔ |
| v3 short course codes | `ef39b51` (2026-08-22) / `relabel_timetable_csv.py` | ✔ |
| v4 CSV relabel + HTML grid | `relabel_timetable_csv.py`, `generate_timetable_html.py` | ✔ (no single commit; the two scripts are the evidence) |
| v5 elective Lec/Lab pairing fix, 63 → 54 offerings | `ef39b51` "Fix elective Lec+Lab pairing"; `solutions/HANDOFF.md` says **63 → 58** | ✘ use **63 → 58** |
| then RL: 25 Java classes + 11 Python modules | `6bf9970` (2026-09-28) "add: rl" — the whole module in one commit | ✔ |

The deck's v1–v5 labels do **not** correspond to git tags (the repo has none) and only loosely to
commits. **Resolution (R).** Present the version history as the seven dated phases reconstructed from
`git log` in `REPO_NOTES.md` §2, and map the deck's v1–v5 labels onto them rather than the reverse.

---

## 16. Minor items

| Item | Note |
|---|---|
| `instructor_identity` scores 0.0 % in the current KPI run | **Name-format artifact**, not a scheduling failure: the evaluator compares `"Joshi, A"` (Taasika, `General.InstructorFormat=last-initial`) with `"Amit Joshi"` (UniTime export). Report as an evaluator limitation. |
| `sectioning_slot_conflicts.py` reports 0 conflicts | It keys on an exact `day start-end` string and misses partial overlaps. Do not cite it. |
| CPSolver `1.4-SNAPSHOT` vs `1.4.94` | `rl/pom.xml` defaults to a local `1.4-SNAPSHOT` build; `rl/SETUP.md` says `1.4.94` from Maven Central is "one trivial commit" behind (an XML-parser security default, no API change) and is a safe substitute. State both. |
| `unitime-out/README.md` says studentInfo has 2,130 students and that student groups are "intentionally omitted" | Both statements are now **out of date**: the current file has 1,130 students and 5,767 group references (commit `222f849`). The README was not updated. |
| Repository name | The folder and remote are `coep-unitime-pilot`; the project is **taasika-v3**. Mention the older name once. |
| `scripts/setup_lunch_breaks.py` | The task spec gives this path; the file actually lives at `scripts/unitime_scripts/setup_lunch_breaks.py`. |
| Term labels Spr6 / Spr10 / Spr11 / Spr12 | Not different semesters — they are successive UniTime *academic sessions* created to re-import the dataset cleanly. All are Spring 2026 (`year="2026"`, session 2026/1/19 – 2026/5/22). Must be explained once, or every table looks inconsistent. |
