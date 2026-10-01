# Fresh-machine setup: through the B1 arm

Scope: steps 1–2 only (instrument B0, sweep the student-conflict weight for B1). No Python
torch/grpc/onnxruntime needed for this — those only matter once you go past B1 into shadow
logging / PPO / the ONNX-policy arms. See `README.md` for the full pipeline.

Assumes you have nothing but a copy of this `rl/` folder. If `runs/B0/seed1/` or
`instances/spr2026.xml` already exist in your copy, skip the steps that (re)create them.

## 0. Prerequisites

- JDK 17+ (`java -version`)
- Maven 3.9+ (`mvn -v`; if missing, unpack a binary distribution anywhere and put its `bin/`
  on `PATH` — no root needed)
- Python 3.10+
- Internet access for the first `mvn package` (downloads dependencies) and for the Maven
  build's own protoc/grpc-java plugin binaries.
- A few GB of free RAM. Each solver run is capped at `-Xmx4g` but typically uses under 1 GB;
  don't run more solver processes at once than `(free_GB - 2) / 1.5` — check with `free -m`
  before raising `--parallel` below.

## 1. Build the jar

```sh
cd rl
mvn -q -DskipTests -Dcpsolver.version=1.4.94 package
ls -la target/unitime-rl-0.1.0-SNAPSHOT-all.jar
```

`-Dcpsolver.version=1.4.94` pulls CPSolver from Maven Central instead of requiring a sibling
`../cpsolver` checkout — this repo's `pom.xml` defaults to a local `1.4-SNAPSHOT` build because
that's what was used for development, but it is one trivial commit ahead of the published
`1.4.94` release (an XML-parser security default, no API change), so `1.4.94` is a safe
substitute. If it ever fails to resolve or breaks, build cpsolver from source instead:
```sh
git clone https://github.com/UniTime/cpsolver.git && cd cpsolver
mvn -q -DskipTests -Dmaven.javadoc.skip=true -Dgpg.skip=true install
cd ../rl && mvn -q -DskipTests package   # no -Dcpsolver.version needed now
```

## 2. Python — light dependencies only

```sh
cd python
python3 -m venv .venv
.venv/bin/pip install -q pandas numpy scipy tabulate
cd ..
```
(Skip `pip install -e .` / `pyproject.toml`'s full dependency list — that pulls in torch,
grpcio, onnxruntime etc., which step 1–2 never touch.)

## 3. Get an instance with students

```sh
grep -c "<student " instances/spr2026.xml
```
If this prints a number in the hundreds/thousands, you're set — that file already has student
enrollments baked in. If it prints `0`, your export has no students (a common UniTime
misconfiguration — the solver's "Student Course Demands" parameter needs to be *Enrolled
Student Course Demands*); export the term's enrollments separately and inject them:
```sh
curl -uUSER:PASS "http://<unitime-host>:8080/UniTime/api/exchange?term=<Term><Year>&type=studentEnrollments" \
  > enrollments.xml
python/.venv/bin/python -m unitime_rl.inject_students \
  --solver-xml instances/<your-export>.xml --enrollments enrollments.xml --out instances/<your-export>.xml
```
(`term` is academic term *then* year, e.g. `Spr62026`, not `2026Spr6`.)

## 4. Step 1 — instrument B0, freeze the objective scales

```sh
java -Xmx2g -jar target/unitime-rl-0.1.0-SNAPSHOT-all.jar \
  --config config/unitime-coep-default.properties \
  --input instances/spr2026.xml --out runs/B0/seed1 --arm B0 --seed 1 \
  --timeout 900 --write-scales --require-students
```
`--timeout` is the wall-clock budget in seconds — 900s (15 min) is enough for this instance to
mostly converge; raise it for a bigger one. `--require-students` makes the run fail loudly
instead of silently reporting C=0 if step 3 was skipped or the export was wrong.

Check the result:
```sh
python3 -c "import json; m=json.load(open('runs/B0/seed1/metrics.json')); print(m['final']['student_violation_rate'], m['wall_clock_sec'])"
```

## 5. Step 2 — B1 weight sweep

```sh
python/.venv/bin/python -m unitime_rl.weight_sweep \
  --jar target/unitime-rl-0.1.0-SNAPSHOT-all.jar \
  --config config/unitime-coep-default.properties \
  --config runs/B0/seed1/scales.properties \
  --instances instances/spr2026.xml \
  --weights 0.2 0.5 1 2 5 10 --seeds 3 --timeout 900 --with-b0 \
  --out runs/sweep --parallel 3 --save-solution
```
Re-running the exact same command resumes it — any job whose `metrics.json` already exists is
skipped. Read the picked weight when it finishes:
```sh
python3 -c "import json; print(json.load(open('runs/sweep/b1_weight.json'))['overall'])"
```
and read `runs/sweep/summary.md` for whether B1 alone already clears the 25% target (if so, the
research question is answered without going any further — see `README.md`).

## Going further

Shadow logging, PPO, ONNX export and the L/R bake-off arms need the full Python stack
(`pip install -e python/`) and are documented in `README.md`'s "Execution order" section, or run
end to end with `./run_pipeline.sh` (same repo, one level up from here).
