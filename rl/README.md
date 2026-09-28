# Learned neighbourhood selection for the COEP UniTime solver

Implementation of `rl doc.pdf`: a policy that chooses among CPSolver's existing neighbourhood
operators, scored by the student-conflict checker, plugged into the solver as a
`NeighbourSelection`. Nothing here writes a placement; every move is proposed by a stock CPSolver
generator and accepted or rejected by CPSolver's Great Deluge, so hard constraints are exactly as
safe as in a normal solve.

```
rl/
  pom.xml                         Maven module "unitime-rl" (Java 17, cpsolver, gRPC, ONNX Runtime)
  src/main/proto/solver_env.proto SolverEnv (Reset/Step) and Policy (Act) services
  src/main/java/org/unitime/timetable/solver/rl/
    RlNeighbourSelection          Neighbour.Class entry point: macro-steps, masks, acceptance, shadow mode, fallback
    Operators, ConflictBiased*    the eight actions (six stock CPSolver operators + two conflict-biased samplers)
    ConflictOracle, ConflictReport the student-conflict checker (incremental) and its report
    SearchMetrics, StateEncoder   metrics of an assignment, the 48-dim state vector, the potential
    RlRuntime                     per-model hooks: dirty lectures, committed count, incumbent metrics
    LexicographicComparator       incumbent rule for training: unassigned, then C, then O
    RlTerminationCondition        wall-clock, iteration, committed-neighbourhood and macro-step budgets
    PolicyClient + OnnxPolicy, GrpcPolicy, BridgePolicy, LinUcbPolicy, SimplePolicies
    HeadlessSolve                 bake-off runner (arms B0 B1 B2 L R SHADOW ...) -> metrics.json
    EnvServer, SolverEnvironment  gRPC training environment (one JVM worker = one resident model)
    SyntheticInstance             COEP-shaped synthetic instance generator for smoke tests
  config/unitime-coep-default.properties   the pilot's UniTime solver configuration (exported from UniTime)
  python/unitime_rl/              gym env, behaviour cloning, Maskable PPO, ONNX export, bake-off tables
  instances/                      timetable XMLs (synthetic ones are generated; real ones come from UniTime)
```

The UniTime-side hook is in the source copy under `org/`:
`CourseTimetablingSolverService` gains `General.SearchAlgorithm=RL`, which sets
`Neighbour.Class=org.unitime.timetable.solver.rl.RlNeighbourSelection` and stops appending
`Suggestion` and `RandomStudentSwap` as side neighbours (they are actions inside the wrapper).
Apply the same two edits to the UniTime build that runs the pilot and drop
`target/unitime-rl-<version>.jar` plus `onnxruntime` into `WEB-INF/lib`.

## Build

Prerequisites: JDK 17+, Maven (the pilot machine has `~/.local/opt/maven/bin/mvn`), Python 3.10+.

```sh
# 1. cpsolver from the sibling clone (or use -Dcpsolver.version=1.4.94 for Maven Central)
(cd ../cpsolver && mvn -q -DskipTests -Dmaven.javadoc.skip=true -Dgpg.skip=true install)
# 2. this module (generates the gRPC stubs, builds the thin jar and the fat jar)
mvn -q -DskipTests package
# 3. python side
cd python && python3 -m venv .venv && .venv/bin/pip install -e . && ./gen_proto.sh
```

`target/unitime-rl-0.1.0-SNAPSHOT-all.jar` is the headless fat jar; `target/unitime-rl-0.1.0-SNAPSHOT.jar`
is the thin jar for UniTime's `WEB-INF/lib`.

## Instances

An instance is **one** file per term: the CPSolver *solver model* XML (root element
`<timetable version="2.5" ...>` with `<rooms>`, `<classes>`, `<groupConstraints>`, `<students>`
and the current assignment). It is self-contained: rooms, instructors, time and room domains,
distribution constraints, students and their enrollments are all inside it, so none of the Data
Exchange files in `unitime-out/` (rooms, staff, offerings, preferences, students) are needed and
they cannot be used instead. **Administration -> Data Exchange** does not produce this format; its
"timetable" export is the class-assignment interchange format (`timetable.dtd`), which the solver
cannot load.

How to get it from UniTime:

0. **Make sure the solver loads students.** The pilot solver configuration has the parameter
   *Student Course Demands* (`Curriculum.StudentCourseDemadsClass`) set to *Projected Student
   Course Demands*, which reads last-like demands and curriculum projections. The COEP session
   has neither, so the solver loads **zero students**, its header says `Student conflicts: 0`
   and the export has an empty `<students/>`. Such an instance is useless here. In
   **Administration -> Solver -> Configurations**, open the course solver configuration used for
   the load and set *Student Course Demands* to **Enrolled Student Course Demands**; this reads
   the `StudentClassEnrollment` rows that `unitime-out/16studentenrollments.xml` imported (check
   they were imported for the same term as the solver load). Reload the solver afterwards. The
   export is right when `grep -c "<student " spr2026.xml` is in the thousands and the header's
   `Student conflicts` is non-zero. `HeadlessSolve` warns on empty instances and
   `--require-students` makes it fail instead.

   Alternative without touching the server configuration: export the enrollments through the
   Data Exchange API and inject them into the solver XML. The class ids in the enrollments export
   are the class ids of the solver XML, so this is the same data *Enrolled Student Course Demands*
   would load.
   ```sh
   curl -uadmin:admin "http://<host>:8080/UniTime/api/exchange?term=Spr62026&type=studentEnrollments" > unitime-out-spr6/studentEnrollments.xml
   python/.venv/bin/python -m unitime_rl.inject_students --solver-xml instances/spr2026-nostudents.xml \
       --enrollments ../unitime-out-spr6/studentEnrollments.xml --out instances/spr2026.xml
   ```
   The `term` value of the API is academic term followed by year (`Spr62026`), not `2026Spr6`.
   On the Spr6 export this produced 990 students with 7,748 enrollments, and the exported
   UniTime solution shows C = 0.531 (526 of 990 students conflicted).
1. **Courses -> Course Timetabling Solver**: load the term with the pilot configuration, let the
   default solve run (or stop it when the solution is complete), then press **Export XML**. That
   button calls `TimetableSolver.exportXml()` and writes exactly the file `HeadlessSolve` and
   `EnvServer` load (the assignment inside becomes the episode's initial solution). It needs the
   `SolverSolutionExportXml` right on the solver group; administrators have it.
2. Before exporting, set **Administration -> Defaults -> Configuration**
   `unitime.solution.export.names=true` (default is false). Without it the export is anonymised:
   class and room names are dropped and only the current solution is saved. The file still loads,
   but debugging and the shadow logs are harder to read. `unitime.solution.export.configuration`
   (default true) embeds the solver configuration in the file; that is fine.
3. Save as `rl/instances/<term>.xml`, for example `spr2026.xml`. Hold out the latest term and one
   department for the generalisation checks in section 4 of the document. A held-out department
   is an export made from a solver loaded with only that department's solver group.

The solver's automatic backups (`unitime.solver.backup` directory, written by `Xml.Save`) are the
same format and also work.

For smoke tests without a UniTime export:

```sh
J=target/unitime-rl-0.1.0-SNAPSHOT-all.jar
java -cp $J org.unitime.timetable.solver.rl.SyntheticInstance instances/synthetic-hard-raw.xml \
     classes=120 students=600 rooms=6 seed=7 domain=5 band=10 take=8 sections=1
# warm-start it with a 3 s stock construction so the XML carries an initial solution
java -jar $J --config config/unitime-coep-default.properties --input instances/synthetic-hard-raw.xml \
     --out runs/warm --arm B0 --timeout 3 --save-solution --quiet
cp runs/warm/solution.xml instances/synthetic-hard.xml
```

## Execution order (section 4 of the document)

`rl/run_pipeline.sh` runs steps 2 to 6 end to end once step 1 exists:

```sh
rl/run_pipeline.sh --train instances/spr2025.xml --heldout instances/spr2026.xml --b0 runs/B0/seed1 \
    --seeds 10 --sweep-seeds 5 --workers 4 --timesteps 300000
```

It takes the wall-clock budget and the frozen scales from the step-1 directory, refuses instances
without students, and skips steps whose outputs already exist. With a single term, pass the same
file as `--train` and `--heldout`; the result is then in-sample only and must be reported as such.
The individual steps follow.

1. **Instrument B0 and freeze the metric.** `HeadlessSolve --arm B0` prints the checker's
   student violation rate `C` (conflicted students over students with two or more assigned
   classes) and `C_checker` (over all students, the denominator of `scripts/eval_timetable_kpis.py`).
   Add `--write-scales` to freeze `Rl.Scale.*` from the baseline and pass the file as an extra
   `--config` to every later run.

   ```sh
   java -jar $J --config config/unitime-coep-default.properties --input instances/spr2026.xml \
        --out runs/B0/seed1 --arm B0 --seed 1 --timeout 1800 --write-scales
   ```

2. **Weight sweep for B1.** Picks the student-conflict weight with the lowest violation rate that
   keeps the assigned ratio within 1 point of B0, and says whether B1 alone clears 25%.

   ```sh
   cd python && .venv/bin/python -m unitime_rl.weight_sweep --jar ../$J \
        --config ../config/unitime-coep-default.properties --instances ../instances/spr2026.xml \
        --weights 0.2 0.5 1 2 5 10 --seeds 5 --timeout 1800 --with-b0 --out runs/sweep --parallel 4
   ```

3. **Shadow-log and behaviour-clone.** SHADOW executes the default selector and logs, per
   macro-step, the state and the operator the default selector effectively used.

   ```sh
   for s in 1 2 3 4 5; do java -jar $J --config config/unitime-coep-default.properties \
        --input instances/spr2025.xml --out runs/shadow/seed$s --arm SHADOW --seed $s --timeout 1800; done
   cd python && .venv/bin/python -m unitime_rl.bc --logs "runs/shadow/*/trajectory.jsonl" --out models/bc_policy.pt
   ```

4. **PPO fine-tune with 4-8 JVM workers.** One `EnvServer` per worker, each on its own port.

   ```sh
   for p in 50051 50052 50053 50054; do
     java -Xmx4g -cp $J org.unitime.timetable.solver.rl.EnvServer --port $p --instances instances \
          --config config/unitime-coep-default.properties --config runs/B0/seed1/scales.properties \
          --set Comparator.StudentConflictWeight=<B1 weight> --set Termination.TimeOut=600 --set Rl.MaxMacroSteps=2000 &
   done
   cd python && .venv/bin/python -m unitime_rl.train_ppo --targets localhost:50051 localhost:50052 localhost:50053 localhost:50054 \
        --instances spr2024 spr2025 --bc-init models/bc_policy.pt --timesteps 300000 --subproc --out models/ppo
   .venv/bin/python -m unitime_rl.export_onnx --ppo models/ppo/maskable_ppo.zip --out models/policy.onnx
   ```

   The `UnassignDiscardCallback` zeroes the policy-gradient contribution of episodes whose final
   assigned ratio fell more than 5 points below the start and logs them to
   `models/ppo/discarded_episodes.jsonl`.

5. **Held-out bake-off with ONNX in-process.** Primary budget is wall-clock (B0's median); run a
   second time with `--max-committed` for the equal-neighbourhood table.

   ```sh
   cd python && .venv/bin/python -m unitime_rl.bakeoff --jar ../$J --config ../config/unitime-coep-default.properties \
        --instances ../instances/spr2026.xml --arms B0 B1 B2 L R --seeds 10 --timeout <B0 median s> \
        --weight <B1 weight> --onnx models/policy.onnx --out runs/bakeoff --parallel 4
   ```

6. `runs/bakeoff/summary.md` holds the paired table (median and IQR per arm, relative reduction of R
   versus B1, co-primary bounds, Wilcoxon with the instance as the unit, secondary metrics).

## Arms

| Arm | `--arm` | Selector | Comparator |
|-----|---------|----------|------------|
| B0 | `B0` | `FixCompleteSolutionNeighbourSelection`, stock weights | native |
| B1 | `B1` | same, `--student-conflict-weight W` (moves `Comparator.`, `Lecture.` and `Placement.NrStudConfsWeight2` together) | native |
| B2 | `B2` | `SimpleSearch` Great Deluge + `RandomStudentSwap` + `Suggestion@0.01` | native |
| L | `L` | `RlNeighbourSelection` with LinUCB over the eight operators | lexicographic |
| R | `R` | `RlNeighbourSelection` with the frozen ONNX policy (`--onnx`) | lexicographic |
| shadow | `SHADOW` | default selector executes, policy only logged (`--onnx` optional) | native |
| diagnostics | `RANDOM`, `ROUNDROBIN`, `FIXED` | RL wrapper with a trivial policy | lexicographic |

`--comparator native|lex` overrides the default per arm.

## Solver properties (all optional)

| Property | Default | Meaning |
|----------|---------|---------|
| `Rl.K` | 50 | solver iterations per macro-step |
| `Rl.Policy` | `onnx` | `onnx`, `grpc`, `linucb`, `random`, `roundrobin`, `fixed`, `bridge`, `none` |
| `Rl.Mode` | `act` | `act` or `shadow` |
| `Rl.Onnx.Path` | | policy file; `Rl.Onnx.Stochastic`, `Rl.Onnx.TimeoutMs` (1.0), `Rl.Onnx.MaxSlowCalls` |
| `Rl.Potential.C/U/H/O` | 1, 0.5, 5, 0.05 | potential weights; `Rl.StepPenalty` 1e-4; `Rl.OClip` 3 |
| `Rl.Scale.*` | first observed value | normalisation of objective terms (freeze with `--write-scales`) |
| `Rl.MaxMacroSteps`, `Rl.MaxCommitted` | -1 | episode truncation and the secondary budget |
| `Rl.DriftCheckInterval` | 20 | full recompute of the incremental checker every N macro-steps |
| `Rl.DisabledOperators` | | comma-separated operator ids to mask permanently |
| `Rl.TrajectoryLog` | | JSONL path (HeadlessSolve sets `<out>/trajectory.jsonl`) |
| `Rl.LinUcb.Alpha/Lambda/RewardScale` | 0.5, 1, 100 | arm L |

## State, actions, reward

The 48 features are listed in `StateEncoder.NAMES` (mirrored in `python/unitime_rl/__init__.py`).
Operators: 0 TimeChange, 1 RoomChange, 2 RandomMove (time and room), 3 TimeSwap, 4 Suggestion,
5 RandomStudentSwap, 6 conflict-biased TimeChange, 7 conflict-biased student swap. An operator that
returns null is masked for the rest of the macro-step and the policy is re-asked with the updated
mask; Suggestion is masked while the solution is complete (it only repairs unassigned classes) and
the student swaps while no class has an alternative section. The reward is the potential
difference of the incumbent, `Phi = -C - 0.5 U - 5 H - 0.05 O`, minus `1e-4` per macro-step; with
the lexicographic comparator the incumbent is what the reward sees.

## Smoke-test results on the synthetic instance (this machine)

Synthetic COEP-shaped instance (120 classes, 600 students in cohorts of 40, 6 rooms), warm-started
from a 3-second stock construction that leaves C = 0.267 with everything assigned; 30 s per run,
one seed. Numbers are only a pipeline check, not evidence for the hypothesis.

| Arm | C after 30 s | assigned | hard | iterations | note |
|-----|-------------|----------|------|------------|------|
| B0 | 0.133 | 1.00 | 0 | 322 | suggestion search dominates the iteration cost |
| B2 | 0.133 | 1.00 | 0 | 198k | |
| RANDOM (RL wrapper) | 0.133 | 1.00 | 0 | 126k | 2,500 macro-steps, 0.27 ms per boundary |
| L | 0.133 | 1.00 | 0 | 205k | 4,100 macro-steps |
| R (BC-only ONNX, 22 samples) | 0.267 | 1.00 | 0 | 244k | policy collapsed to RoomChange; forward pass 0.08 ms |

Environment throughput through gRPC: about 100 macro-steps per second per worker, reset in under
a second (in-memory restore of placements and sectioning), which is far above the "few thousand
macro-steps per hour" floor in section 5 of the document. A 4,000-step Maskable PPO run against one
worker (BC warm start, 40-macro-step episodes) trains, exports to ONNX (max deviation 2e-6) and runs
in-JVM in arm R; with that budget the policy has not moved away from the BC prior yet.

Tests: `mvn test` (incremental oracle equals a full recompute over 200 random move batches; state
vector dimension), `python/tests/test_policy_net.py` (BC weights load into the PPO actor, ONNX
matches torch) and `python/tests/test_env_smoke.py` (needs a running EnvServer; episode, mask,
reset determinism).

## Notes and deviations

* The lexicographic incumbent rule skips the hard-violation key, because `Basic.DisobeyHard` is
  false and all operators use CPSolver's hard filter; `H` is still computed once per macro-step
  and enters the potential and the state.
* One solver iteration inside a macro-step is one call of `selectNeighbour`, which for the Great
  Deluge means one committed (or no-op) neighbourhood; rejected proposals are counted in
  `proposals` in the trajectory log.
* The B1 weight moves the comparator weight and the two placement-selection weights of the stock
  solver together; pass individual `--set` overrides to sweep them separately.
* `Suggestion` (operator 4) in CPSolver only proposes moves for unassigned classes, so on a complete
  timetable it is masked; the document's operator table is otherwise implemented as written.
