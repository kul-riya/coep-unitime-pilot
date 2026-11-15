# OUTLINE — Semester VII B.Tech. Project Report, "taasika-v3"

Title: **University Course Timetabling System** · Semester VII · AY 2026–2027 · Guide: Abhijit A. M.
Team: Mihir Shah, Riya Kulkarni, Ved Mundhada, Akshay Sathaye.
Target: 20–30 pages. Formal, third person, past tense for work done.

Evidence keys: **[R]** repo (verified this session) · **[Rf]** repo file, quoted not re-run ·
**[S6]** Semester VI report · **[D]** deck (only where §13 of `DISCREPANCIES.md` confirms it) ·
**[T]** `\todo{}`.

---

## Front matter
| Item | Content | Evidence |
|---|---|---|
| Cover | COEP logo placeholder, university, department, title, "Semester VII B.Tech. Project Report", AY 2026–2027, Semester VII, guide, 4 team members | task spec |
| Abstract | ~200 words: Sem VI established feasibility; Sem VII built the pipeline, constraints, evaluation framework and RL layer; headline = 291 classes scheduled, 0 instructor/room conflicts, 40/1130 students conflicted under pinned enrollments; the RL control experiment answered its own research question in the negative | [R] |
| ToC, List of Figures, List of Tables | auto | — |

## 1 Introduction (~1.5 pp)
NP-hardness; COEP's heterogeneous structure; **recap of Semester VI** (deployment, constraint
mapping, feasibility study — all constraints expressible, no relaxation needed) **[S6]**; then the
Semester VII contributions as a bulleted list: end-to-end Taasika→UniTime pipeline, institution
constraint encoding, the KPI evaluation framework, the pinned-enrollment result, the RL layer.
State the project name **taasika-v3** and note once that the repository folder is still
`coep-unitime-pilot`. **[R §DISCREPANCIES 16]**

## 2 Problem Definition (~1.5 pp)
Hard vs soft constraints. The *quality* problem that motivates this semester: a feasible timetable
is not enough — student conflicts persist, and measuring them honestly is itself hard because the
solver will silently re-section students to make the number look like zero. Forward-reference §10.
**[S6]** for the formal setting, **[R]** for the quality problem.

## 3 Overview of UniTime and CPSolver (~2.5 pp)
Tightened reuse of **[S6]** §3 and §7: the four UniTime components, the solver library, IFS,
Conflict-based Statistics. Define UniTime, CPSolver, IFS, CBS, KPI on first use.
- Table: CPSolver variable = `Lecture`, value = `Placement` (time + room); students are not
  variables; same-student overlap is priced by `JenrlConstraint`. **[R]**
- **Figure 1 (TikZ): solver iteration loop** — Stop Check → Propose Move → Move Selected? →
  Apply Move / Advance Counter → Score → Is Better? → Save Best. (explicitly requested)
- Listing: IFS pseudocode, carried over from **[S6]** Listing 1.
- Conflict rule box: shared day bit AND overlapping slot interval (touching endpoints excluded)
  AND shared week bit when both have date patterns. **[R]**

## 4 System Setup and Configuration (~1.5 pp)
Table of the stack with a **"used where"** column, resolving the Java question explicitly:
Java 21 + MySQL 8.4 + Tomcat 9.0 for the UniTime server **[S6]**; Java 17
(`maven.compiler.release=17`, "JDK 17+") for the `unitime-rl` module **[R: rl/pom.xml, SETUP.md]**;
Maven 3.9+, Python 3.10+, CPSolver 1.4-SNAPSHOT / 1.4.94, gRPC 1.84.0, protobuf 4.36.2,
ONNX Runtime 1.30.0. One paragraph stating these are complementary, not contradictory.
**[DISCREPANCIES §2]**

## 5 Data Pipeline: Taasika → UniTime (~3 pp)
- Taasika schema analysis and mapping. **Figure 2** = existing `taasika-schema.png`,
  **Figure 3** = existing `unitime-schema.png`. **[Rf]**
- **Figure 4 (TikZ): pipeline diagram** — `taasika3.sql` → `taasika_loader` → 8 generators →
  16 XML → validators → `0gen_all.zip` → Data Exchange → solver → CSV/XML → KPI evaluator.
- Table: the 16 ordered imports and why order matters (full list → Appendix A). **[R]**
- Design decisions table: Lec+Lab merging rule, Indian credit formula
  `1 cr/lec hr + 0.5 cr/lab hr`, building inference heuristic, instructor `positionType` from
  `minHrs`, student simulation `61yy03aaa`, elective handling. **[R: unitime-out/README.md + code]**
- One-command entry point `python scripts/gen_all.py --term Spr12` and the three validators.
  Also `scripts/zip_0gen_all.py` for re-targeting the term without regenerating. **[R]**
- Operational pitfalls that cost real time: zip must be flat; buildings need
  **Administration → Academic Sessions → Buildings → Update Data**; `13preferences.xml` is
  mandatory or ~0 variables load; term code is `Spr122026` not `2026Spr12`. **[R]**

## 6 Institution-Specific Constraints (~2.5 pp)
- Carry over **[S6]** Table 1 (constraint → UniTime mechanism) as the *inherited* table.
- New table: what was **actually implemented**, with the `FIXED_ENTRIES_MAP` rules verbatim
  (MDM_Required Mon/Tue 16:30–18:30 R; OE_Required Mon/Tue 09:30–10:30 R; Non_MDM_Prohibited;
  SY_Non_OE_Prohibited) and the time-pattern mapping function. **[R: gen_preferences.py]**
- Lunch breaks: dynamic 1-hour window 11:30–15:30 for students *and* instructors, installed as
  solver criteria by the Jython script, not as a time-pattern exclusion. **[R]**
- Student groups: group code = class `scheduleNote`; 242 groups; what groups do and do **not** do
  (they change sectioning only via a group reservation; `Student.getDistance` is the only place
  `getGroups()` affects coursett sectioning). **[R]**
- Shared multi-instructor labs. **[S6]** §8.2.

## 7 Datasets Used (~2 pp)
The verified `unitime-out/0gen_all` inventory table (16 files, sizes, counts) — term Spr12, 56
offerings, 291 classes, 1,130 students, 9,148 enrollments, 242 groups, 115 staff, 6 buildings,
42 rooms. **[R, verified]**
Student population breakdown and the `intake.py` headcount rules. Source snapshot **242**
(`published-v4-26jan26`, `taasika3.sql`) with the evidence (43 classes + 199 batches = 242 groups;
115 teachers) and a note that the `created=` string in the XML is a stale hard-coded "240".
**[DISCREPANCIES §9]**
Short table of the *other* instances used in experiments (Spr6/990/262, Spr10/1130/290, Spr11) and
one sentence explaining that Spr6…Spr12 are successive UniTime sessions, not different semesters.
**[DISCREPANCIES §16]**

## 8 Simulation, Testing and UniTime Debugging (~2 pp)
- Why students had to be simulated; the preference-based enrollment simulation; `assign_within_limits`
  overflow behaviour and the resulting cross-division lab batches. **[R]**
- UniTime's Course Offering → Instructional Offering → Configuration → Subpart → Class hierarchy.
- Debugging log, each with cause and fix: "has no available room (class not loaded)";
  classes not loading without preferences; Hibernate `TransientObjectException` on large group
  merges; `incremental="true"` still running `deleteUnmatchedClasses`; anonymised solver export
  unless `unitime.solution.export.names=true`; zero students loaded under *Projected Student
  Course Demands*. **[R]**
- The three pinning settings and the loader mechanics (`addLecture` only when
  `hasOffering && canEnroll`; `InitialSectioning` skips already-enrolled students). **[R]**

## 9 Evaluation Framework and Tools (~2 pp)
- Why an external evaluator was needed (the solver grades itself).
- `eval_timetable_kpis.py`: CSV mode vs XML mode, and the warning that the two have different
  denominators. 10 hard checks + 3 preference checks + efficiency metrics → formulas in Appendix C.
- Cross-validation result: Java `ConflictOracle` 0.026262626 vs Python evaluator 0.026263 (26/990)
  on the same `solution.xml` — exact agreement, two independent implementations. **[R, strong]**
- Supporting tools: `convert_xml_to_csv.py`, `relabel_timetable_csv.py`,
  `generate_timetable_html.py`, `verify_time_patterns.py`, `validate_*`.
- **Figure 5 (TikZ):** the Generate → Simulate → Analyse → Evaluate → Refine → Regenerate loop.
- Known evaluator limitations: `instructor_identity` name-format artifact (0.0 % is spurious);
  `sectioning_slot_conflicts.py` misses partial overlaps. **[R]**

## 10 Experiments and Results (~4 pp) — the core of the report
1. **Solver checker vs KPI evaluator** — 526/990 (53.1 %) vs 587/1,290 (45.5 %); reconcile by
   instance and denominator. **[R, DISCREPANCIES §6]**
2. **StudentConflictWeight in the UniTime UI** — weight 5 → 676/1,290, weight 20 → 894/1,290, with
   the caveat that the CSV join used the old enrollment sections, so this is *not* a controlled
   comparison. Correct the deck's 614. **[R, DISCREPANCIES §4]**
3. **The controlled weight sweep (headless, instance fixed)** — the `rl/runs/sweep` table, B0
   median C = 0.0414, initial C = 0.5313, best weight 5 (C = 0) per the recorded summary, with the
   footnote that recomputation from the per-seed files gives weight 2 (C = 0.0030); both clear the
   25 % bar. **Figure 6 (pgfplots): C vs weight**, median with per-seed points. **[R]**
4. **The "0 conflicts" analysis — why it is NOT an improvement.** Table of the four
   zero-conflict artifacts with the mechanism for each (re-sectioning / already-solved instance /
   zero students loaded / different instance). **[R, DISCREPANCIES §7]**
5. **The pinned-enrollment result (headline).** Full verified KPI table for
   `spr2026_11_all_flags.csv` against `0gen_all`: 291 classes, 290 assigned, hard feasibility 98.85,
   0 instructor and 0 room conflicts, **40/1,130 students (3.54 %)**, 63 student lunch violations.
   Breakdown of the 40 conflicts (all FY, `PPS-FY Lab` × `FY-Reserve Lec`, four lab/lecture pairs).
   **Figure 7 (pgfplots): bar chart of hard-check pass rates.** **[R, verified]**
6. **Cross-run comparison table** of every KPI artifact with instance, students, classes and rate,
   so no number floats free of its denominator. **[R]**
Each sub-section ends with an explicit, honest interpretation.

## 11 Reinforcement-Learning Layer (~3 pp)
Define MDP, PPO, ONNX, gRPC on first use.
- Research question and hypothesis; the pre-registered 25 % success criterion.
- **Design invariant**: nothing writes a placement; every move comes from a stock CPSolver
  generator and is accepted/rejected by Great Deluge, so hard-constraint safety is unchanged. **[R]**
- MDP: 48-feature state (`StateEncoder.NAMES`, grouped into conflict / schedule / search /
  history features), 8 operators, K = 50 iterations per macro-step, potential-based reward
  `Phi = -C - 0.5U - 5H - 0.05O` minus `1e-4` per step. **Figure 8 (TikZ): MDP + training/production
  architecture** (EnvServer gRPC workers ↔ Maskable PPO; frozen ONNX in-JVM for production, with
  fallback). **[R]**
- Arms table B0/B1/B2/L/R/SHADOW with selector and comparator.
- Trained artifacts: BC prior, 100,000-timestep PPO on 3 workers, ONNX export.
- **Explicitly separated status:**
  - *Implemented*: all 25 Java classes, 11 Python modules, both policies, the environment, masking,
    the oracle (unit-tested against full recompute over 200 random move batches).
  - *Measured on synthetic data only*: throughput ~100 macro-steps/s/worker, reset < 1 s, ONNX
    forward 0.08 ms, torch–ONNX deviation 2e-6; all arms tie at C = 0.133, arm R *worse* at 0.267.
  - *Measured on real data*: B0/B1/B2 only; and the B1 control **answered the research question in
    the negative** — weight tuning alone clears 25 %, so the learned policy was not required.
  - *Hypothesis / not done*: arms L and R on a COEP instance; a held-out term; shadow logs.
- **No claim that RL beats the baselines.** **[DISCREPANCIES §14]**

## 12 Implementation History and Codebase Overview (~2 pp)
- Version history table: the seven dated phases from `git log` (30 commits, 2026-06-23 → 2026-10-08,
  two authors), with the deck's v1–v5 labels mapped onto them and the 63 → 58 correction.
  **[R §REPO_NOTES 2, DISCREPANCIES §15]**
- Repo layout table; **Figure 9 (TikZ): system architecture**.
- Script inventory table (what each of the 25 Python scripts + 2 Jython scripts does).
- The generation workflow as a numbered procedure, in the style of **[S6]** §9, updated:
  generate → validate → zip → import (16 steps, Update Data for buildings, Manage Instructor List)
  → set the three solver flags → load → solve → export → evaluate.
- The new group-membership implementation (commit `222f849`) and the 40-conflict outcome.

## 13 Limitations (~1 p)
Simulated (not MIS) students; single department; one real instance; snapshot provenance string
stale; 40 FY conflicts unresolved; `PPS-FY Lec` 200 unplaced and `PSEC2-EAI Lab` over-subscribed by
2; `BT-Div1`/`BT-Div2`/`FY-PP1-A_` groups empty; room-preference hit rate 12.6 % and the spurious
instructor-identity 0 %; `PP-FY Lab 16–41` still present; RL untested on real data; no held-out term;
`sweep` seed-1 artifact inconsistency. **[R]**

## 14 Future Scope (~1.5 pp)
Carry-over table from **[S6]** §10 with a status column:
| Item | Status |
|---|---|
| Examination scheduling | still open |
| Calendar (.ics) integration | still open |
| University-wide deployment | still open (single department) |
| Automated change notification | still open |
| WhatsApp group automation | still open |
| Student data pipeline from MIS | **partly done** — pipeline built and exercised on simulated data |
| Course definition interface | **partly done** — XML generation automated; no instructor-facing UI |
| Constraint mapping validated | **done** (Sem VI) and now encoded in `gen_preferences.py` |
New items: student sectioning with pre-defined batches; multi-teacher same-time-same-room labs;
one-click Taasika snapshot → final solution XML (currently three scripts); solution XML → Taasika
snapshot format; soft-constraint optimisation (room preference is the weak KPI); completing the
RL bake-off with arms L and R on a held-out term.

## 15 Conclusion (~0.75 p)
What was built, what was measured, what the negative RL result means, and what it enables next.
No marketing language.

## References
Keep **[S6]**'s three: Müller/Rudová/Barták PATAT 2006; Müller ITC2007; UniTime Course Entry manual.
Add: UniTime Data Exchange / XML interface docs, CPSolver repository, Schulman et al. PPO,
Gymnasium, Stable-Baselines3 / sb3-contrib MaskablePPO, ONNX Runtime, gRPC, Li et al. LinUCB.
Any uncertain bibliographic detail gets `\todo{verify}`.

## Appendices
- **A** — the 16 XML imports: file, root element, what it creates, why it must come at that position.
- **B** — Spr6 file inventory table (the instance behind the RL experiments): 262 classes, 990
  students, 44 rooms, `rl/instances/spr2026.xml`, plus the `solutions/` artifacts derived from it.
- **C** — KPI definitions: formula for each of the 10 hard checks, 3 preference checks and the
  efficiency metrics, plus the hard-feasibility and preference aggregate formulas.
- **D** — Evidence table: every numeric claim in the report → the file (and command) it came from.

---

## Figure plan
| # | Figure | How produced |
|---|---|---|
| 1 | Solver iteration loop flowchart | TikZ |
| 2 | Taasika ER schema | existing `taasika-schema.png` |
| 3 | UniTime ER schema | existing `unitime-schema.png` |
| 4 | Taasika→UniTime pipeline | TikZ |
| 5 | Generate→Evaluate→Refine loop | TikZ |
| 6 | Student violation rate vs conflict weight | pgfplots from `rl/runs/sweep` |
| 7 | Hard-check pass rates of the final solution | pgfplots from the verified KPI run |
| 8 | RL MDP + training/production architecture | TikZ |
| 9 | System architecture | TikZ |

Root-level PNGs `image.png`, `image (1).png`, `image (2).png`, `Screenshot 2026-04-13 165841.png`
are **not** used unless opened and truthfully captioned.
