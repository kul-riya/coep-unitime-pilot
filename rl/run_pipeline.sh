#!/usr/bin/env bash
# Execution order of the research document, steps 2-6, for one training instance and one held-out
# instance. Step 1 (B0 instrumentation, --write-scales) must have been run already; its output
# directory supplies the wall-clock budget (B0 median runtime) and the frozen scales.
#
#   rl/run_pipeline.sh --train instances/spr2025.xml --heldout instances/spr2026.xml \
#        --b0 runs/B0/seed1 --seeds 10 --sweep-seeds 5 --workers 4 --timesteps 300000
#
# Every step writes under runs/<name>/ and is skipped when its output already exists, so the script
# can be re-run after a failure. Set DRY=1 to print the commands only.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opt/maven/bin:$PATH"

TRAIN=(); HELDOUT=(); B0DIR=runs/B0/seed1; SEEDS=10; SWEEP_SEEDS=5; WORKERS=4; TIMESTEPS=300000
TIMEOUT=""; K=50; MAX_MACRO=2000; WEIGHTS="0.2 0.5 1 2 5 10"; PARALLEL=4; SHADOW_SEEDS=5; OUT=runs; COMMITTED_SEEDS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --train) TRAIN+=("$2"); shift 2;;
    --heldout) HELDOUT+=("$2"); shift 2;;
    --b0) B0DIR="$2"; shift 2;;
    --seeds) SEEDS="$2"; shift 2;;
    --committed-seeds) COMMITTED_SEEDS="$2"; shift 2;;
    --sweep-seeds) SWEEP_SEEDS="$2"; shift 2;;
    --shadow-seeds) SHADOW_SEEDS="$2"; shift 2;;
    --workers) WORKERS="$2"; shift 2;;
    --timesteps) TIMESTEPS="$2"; shift 2;;
    --timeout) TIMEOUT="$2"; shift 2;;
    --k) K="$2"; shift 2;;
    --max-macro-steps) MAX_MACRO="$2"; shift 2;;
    --weights) WEIGHTS="$2"; shift 2;;
    --parallel) PARALLEL="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown argument $1"; exit 2;;
  esac
done
[ ${#TRAIN[@]} -gt 0 ] || { echo "--train instance.xml is required"; exit 2; }
[ ${#HELDOUT[@]} -gt 0 ] || HELDOUT=("${TRAIN[@]}")
[ -n "$COMMITTED_SEEDS" ] || COMMITTED_SEEDS=$SEEDS

JAR=target/unitime-rl-0.1.0-SNAPSHOT-all.jar
CFG=(--config config/unitime-coep-default.properties)
[ -f "$B0DIR/scales.properties" ] && CFG+=(--config "$B0DIR/scales.properties")
PY=python/.venv/bin/python
run() { echo "+ $*"; [ "${DRY:-0}" = 1 ] || "$@"; }

[ -f $JAR ] || run mvn -q -DskipTests package

# budget = B0 median runtime, unless given
if [ -z "$TIMEOUT" ]; then
  TIMEOUT=$(python3 -c "import json,sys; print(int(round(json.load(open(sys.argv[1]))['wall_clock_sec'])))" "$B0DIR/metrics.json")
fi
echo "wall-clock budget: ${TIMEOUT}s (from $B0DIR)"

# sanity: every instance must carry students, or the conflict metric is undefined
for inst in "${TRAIN[@]}" "${HELDOUT[@]}"; do
  n=$(grep -c "<student " "$inst" || true)
  if [ "$n" = 0 ]; then
    echo "ERROR: $inst has no <student> elements. Export it from a solver loaded with"
    echo "       'Student Course Demands' = 'Enrolled Student Course Demands' (see README, Instances)."
    exit 1
  fi
done

echo "== step 2: B1 weight sweep on the held-out instance(s)"
if [ ! -f $OUT/sweep/b1_weight.json ]; then
  run $PY -m unitime_rl.weight_sweep --jar $JAR "${CFG[@]}" --instances "${HELDOUT[@]}" \
      --weights $WEIGHTS --seeds $SWEEP_SEEDS --timeout $TIMEOUT --with-b0 --out $OUT/sweep --parallel $PARALLEL
fi
WEIGHT=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['overall'])" $OUT/sweep/b1_weight.json)
echo "B1 weight: $WEIGHT"
grep -h "clear" $OUT/sweep/summary.md || true

echo "== step 3: shadow logs on the training instance(s), behaviour cloning"
shadow_pids=()
for inst in "${TRAIN[@]}"; do
  name=$(basename "$inst" .xml)
  for s in $(seq 1 $SHADOW_SEEDS); do
    d=$OUT/shadow/$name/seed$s
    if [ ! -f $d/metrics.json ]; then
      mkdir -p "$d"
      echo "+ java ... --arm SHADOW --seed $s --out $d (background)"
      if [ "${DRY:-0}" != 1 ]; then
        java -Xmx4g -jar $JAR "${CFG[@]}" --input "$inst" --out $d --arm SHADOW --seed $s \
            --timeout $TIMEOUT --k $K --student-conflict-weight $WEIGHT --quiet > "$d/stdout.log" 2>&1 &
        shadow_pids+=($!)
      fi
    fi
    # cap concurrency at PARALLEL, same as every other stage
    while [ "${#shadow_pids[@]}" -ge "$PARALLEL" ]; do
      wait -n "${shadow_pids[@]}" 2>/dev/null || true
      alive=(); for p in "${shadow_pids[@]}"; do kill -0 "$p" 2>/dev/null && alive+=("$p"); done
      shadow_pids=("${alive[@]}")
    done
  done
done
for p in "${shadow_pids[@]}"; do wait "$p" 2>/dev/null || true; done
[ -f models/bc_policy.pt ] || run $PY -m unitime_rl.bc --logs "$OUT/shadow/*/*/trajectory.jsonl" --out models/bc_policy.pt

echo "== step 4: PPO fine-tune with $WORKERS JVM workers"
if [ ! -f models/ppo/maskable_ppo.zip ]; then
  PORTS=(); PIDS=()
  for i in $(seq 0 $((WORKERS-1))); do
    port=$((50051+i)); PORTS+=("localhost:$port")
    run java -Xmx4g -cp $JAR org.unitime.timetable.solver.rl.EnvServer --port $port --instances instances "${CFG[@]}" \
        --set Comparator.StudentConflictWeight=$WEIGHT --set Lecture.StudentConflictWeight=$WEIGHT --set Placement.NrStudConfsWeight2=$WEIGHT \
        --set Termination.TimeOut=$TIMEOUT --set Rl.MaxMacroSteps=$MAX_MACRO --set Rl.K=$K --no-log &
    PIDS+=($!)
  done
  trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT
  sleep 8
  INST_NAMES=(); for inst in "${TRAIN[@]}"; do INST_NAMES+=("$(basename "$inst" .xml)"); done
  run $PY -m unitime_rl.train_ppo --targets "${PORTS[@]}" --instances "${INST_NAMES[@]}" --bc-init models/bc_policy.pt \
      --timesteps $TIMESTEPS --subproc --out models/ppo
  kill "${PIDS[@]}" 2>/dev/null || true; trap - EXIT
fi
[ -f models/policy.onnx ] || run $PY -m unitime_rl.export_onnx --ppo models/ppo/maskable_ppo.zip --out models/policy.onnx

echo "== step 5: held-out bake-off, wall-clock budget (primary)"
run $PY -m unitime_rl.bakeoff --jar $JAR "${CFG[@]}" --instances "${HELDOUT[@]}" --arms B0 B1 B2 L R \
    --seeds $SEEDS --timeout $TIMEOUT --weight $WEIGHT --onnx models/policy.onnx --k $K --out $OUT/bakeoff-wallclock --parallel $PARALLEL

echo "== step 5b: held-out bake-off, equal committed neighbourhoods (secondary)"
# B0's median committed neighbourhoods under the same wall-clock budget (from the sweep's B0 runs)
COMMITTED=$(python3 - "$OUT/sweep/B0" <<'EOF'
import glob, json, statistics, sys
vals = [json.load(open(f))["committed"] for f in glob.glob(sys.argv[1] + "/*/B0/seed*/metrics.json")]
print(int(statistics.median(vals)) if vals else 0)
EOF
)
echo "committed budget: $COMMITTED"
run $PY -m unitime_rl.bakeoff --jar $JAR "${CFG[@]}" --instances "${HELDOUT[@]}" --arms B0 B1 B2 L R \
    --seeds $COMMITTED_SEEDS --max-committed $COMMITTED --weight $WEIGHT --onnx models/policy.onnx --k $K --out $OUT/bakeoff-committed --parallel $PARALLEL

if [ "${TRAIN[*]}" != "${HELDOUT[*]}" ]; then
  echo "== step 6: generalisation gap (training instances under the same budget)"
  run $PY -m unitime_rl.bakeoff --jar $JAR "${CFG[@]}" --instances "${TRAIN[@]}" --arms B1 R \
      --seeds $SEEDS --timeout $TIMEOUT --weight $WEIGHT --onnx models/policy.onnx --k $K --out $OUT/bakeoff-train --parallel $PARALLEL
else
  echo "== step 6 skipped: training and held-out instances are the same file, so every result is in-sample"
fi

echo "done. Tables: $OUT/bakeoff-wallclock/summary.md, $OUT/bakeoff-committed/summary.md"
