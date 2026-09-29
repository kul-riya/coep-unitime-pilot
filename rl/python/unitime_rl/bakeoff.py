"""Paired bake-off across arms, instances and seeds; produces the results table of section 4.

    python -m unitime_rl.bakeoff --jar ../target/unitime-rl-0.1.0-SNAPSHOT-all.jar \
        --config ../config/unitime-coep-default.properties \
        --instances instances/spr2026.xml --arms B0 B1 B2 L R --seeds 10 --timeout 600 \
        --weight 1.0 --onnx models/policy.onnx --out runs/bakeoff --parallel 4

Primary budget: --timeout (wall-clock, set to B0's median runtime). Secondary budget: --max-committed
(equal number of committed neighbourhoods). Run twice and report both tables.

Metrics per run come from HeadlessSolve's metrics.json. The summary reports median and IQR across
seeds per arm and instance, the relative reduction (C_B1 - C_R) / C_B1 on per-instance medians, the
co-primary bounds, and a paired Wilcoxon signed-rank test with the instance as the unit (needs >= 2
instances; with one instance the per-seed pairing is reported as exploratory).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.stats import wilcoxon
except Exception:  # pragma: no cover
    wilcoxon = None

ARMS_NEEDING_WEIGHT = {"B1", "B2", "L", "R"}


def run_one(jar, config, instance, arm, seed, out_dir, timeout, max_committed, weight, onnx, java, extra_sets, k):
    out = Path(out_dir) / Path(instance).stem / arm / f"seed{seed}"
    metrics = out / "metrics.json"
    if metrics.exists():
        return json.loads(metrics.read_text())
    out.mkdir(parents=True, exist_ok=True)
    cmd = [java, "-Xmx4g", "-jar", jar, "--input", instance, "--out", str(out), "--arm", arm, "--seed", str(seed), "--quiet"]
    for c in config:
        cmd += ["--config", c]
    if timeout is not None:
        cmd += ["--timeout", str(timeout)]
    if max_committed is not None:
        cmd += ["--max-committed", str(max_committed)]
    if arm in ARMS_NEEDING_WEIGHT and weight is not None:
        cmd += ["--student-conflict-weight", str(weight)]
    if arm == "R":
        if not onnx:
            raise SystemExit("--onnx is required for arm R")
        cmd += ["--onnx", onnx]
    if k:
        cmd += ["--k", str(k)]
    for s in extra_sets:
        cmd += ["--set", s]
    with open(out / "stdout.log", "w") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    if rc != 0 or not metrics.exists():
        print(f"[bakeoff] FAILED {instance} {arm} seed={seed} (rc={rc}); see {out / 'stdout.log'}", file=sys.stderr)
        return None
    return json.loads(metrics.read_text())


def flatten(m: dict) -> dict:
    f = m["final"]
    return {
        "instance": Path(m["input"]).stem, "arm": m["arm"], "seed": m["seed"],
        "C": f["student_violation_rate"], "C_checker": f["checker_violation_rate"], "pair_rate": f["pair_violation_rate"],
        "zero_conflict_fraction": f["zero_conflict_fraction"], "assigned_ratio": f["assigned_ratio"], "hard": f["hard_violations"],
        "soft_penalty": f["soft_penalty"], "time_pref": f["time_pref"], "room_pref": f["room_pref"], "dist_pref": f["dist_pref"],
        "total_value": f["total_value"], "wall_clock_sec": m["wall_clock_sec"], "iterations": m["iterations"], "committed": m["committed"],
        "reach_0.40": (m.get("thresholds", {}).get("first_reach_0.40") or {}).get("macro_step"),
        "reach_0.30": (m.get("thresholds", {}).get("first_reach_0.30") or {}).get("macro_step"),
        "reach_0.25": (m.get("thresholds", {}).get("first_reach_0.25") or {}).get("macro_step"),
        "last_c_improvement_sec": (m.get("c_history") or [{}])[-1].get("time_sec") if m.get("c_history") else None,
        "fallback": (m.get("rl") or {}).get("fallback"),
        "disagreement_rate": (m.get("rl") or {}).get("disagreement_rate"),
    }


def iqr(x):
    q = np.percentile(x, [25, 75])
    return q[1] - q[0]


def summarise(df: pd.DataFrame, out: Path, reference: str = "B1", claim: str = "R", threshold: float = 0.25):
    lines = []
    g = df.groupby(["instance", "arm"])
    table = g.agg(C_median=("C", "median"), C_iqr=("C", iqr), C_checker_median=("C_checker", "median"),
                  assigned_median=("assigned_ratio", "median"), hard_max=("hard", "max"), soft_median=("soft_penalty", "median"),
                  wall_median=("wall_clock_sec", "median"), committed_median=("committed", "median"), n=("seed", "count"))
    lines.append("## Per instance and arm (median over seeds, IQR for C)\n")
    lines.append(table.round(4).to_markdown())
    lines.append("")

    # relative reduction of claim vs reference on per-instance medians
    piv = table["C_median"].unstack("arm")
    rows = []
    for inst, r in piv.iterrows():
        if reference in r and claim in r and r[reference] > 0:
            rows.append({"instance": inst, f"C_{reference}": r[reference], f"C_{claim}": r[claim], "relative_reduction": (r[reference] - r[claim]) / r[reference]})
    rel = pd.DataFrame(rows)
    lines.append(f"## Relative reduction of {claim} versus {reference}: (C_{reference} - C_{claim}) / C_{reference}\n")
    if not rel.empty:
        lines.append(rel.round(4).to_markdown(index=False))
        med_rel = float(rel["relative_reduction"].median())
        lines.append(f"\nMedian relative reduction across instances: **{med_rel:.3f}** (threshold {threshold:.2f}) -> {'PASS' if med_rel >= threshold else 'FAIL'}")
        if wilcoxon is not None and len(rel) >= 2:
            a = piv.loc[rel['instance'], reference].values
            b = piv.loc[rel['instance'], claim].values
            try:
                stat, p = wilcoxon(a, b, alternative="greater")
                lines.append(f"Paired Wilcoxon signed-rank (instance as unit, H1: C_{reference} > C_{claim}): W={stat:.1f}, p={p:.4f}, n={len(rel)}")
            except ValueError as e:
                lines.append(f"Wilcoxon not computed: {e}")
        else:
            lines.append("Wilcoxon with the instance as unit needs >= 2 instances; exploratory per-seed pairing below.")
            one = df[df.arm.isin([reference, claim])]
            if len(one.instance.unique()) == 1 and wilcoxon is not None:
                a = one[one.arm == reference].sort_values("seed")["C"].values
                b = one[one.arm == claim].sort_values("seed")["C"].values
                n = min(len(a), len(b))
                if n >= 2:
                    try:
                        stat, p = wilcoxon(a[:n], b[:n], alternative="greater")
                        lines.append(f"Exploratory per-seed Wilcoxon: W={stat:.1f}, p={p:.4f}, n={n}")
                    except ValueError as e:
                        lines.append(f"Wilcoxon not computed: {e}")
    else:
        lines.append(f"(arms {reference} and/or {claim} missing)")
    lines.append("")

    # co-primary bounds, per instance
    lines.append("## Co-primary bounds (held-out term)\n")
    co = []
    for inst in piv.index:
        t = table.loc[inst]
        if reference not in t.index or claim not in t.index:
            continue
        ref, cl = t.loc[reference], t.loc[claim]
        b0_wall = table.loc[inst].loc["B0"]["wall_median"] if "B0" in t.index else np.nan
        co.append({
            "instance": inst,
            "assigned_within_1pt": bool(cl["assigned_median"] >= ref["assigned_median"] - 0.01),
            "hard_zero": bool(cl["hard_max"] == 0),
            "soft_within_10pct": bool(cl["soft_median"] <= 1.10 * ref["soft_median"]) if ref["soft_median"] > 0 else True,
            "wall_within_2x_B0": bool(cl["wall_median"] <= 2.0 * b0_wall) if not np.isnan(b0_wall) else None,
        })
    if co:
        lines.append(pd.DataFrame(co).to_markdown(index=False))
    lines.append("")

    # secondary metrics
    lines.append("## Secondary metrics (median over seeds)\n")
    sec = df.groupby(["instance", "arm"]).agg(zero_conflict=("zero_conflict_fraction", "median"), pair_rate=("pair_rate", "median"),
                                              reach_040=("reach_0.40", "median"), reach_030=("reach_0.30", "median"), reach_025=("reach_0.25", "median"),
                                              last_c_improvement_sec=("last_c_improvement_sec", "median"),
                                              disagreement=("disagreement_rate", "median"))
    lines.append(sec.round(4).to_markdown())
    lines.append("")
    if "B0" in df.arm.unique():
        b0 = df[df.arm == "B0"].groupby("instance")["iterations"].median()
        oh = []
        for inst, grp in df.groupby("instance"):
            for arm, g2 in grp.groupby("arm"):
                if inst in b0.index and b0[inst] > 0:
                    # overhead ratio = B0 iteration time / arm iteration time  (iterations per second inverted)
                    it_b0 = b0[inst] / df[(df.arm == "B0") & (df.instance == inst)]["wall_clock_sec"].median()
                    it_arm = g2["iterations"].median() / g2["wall_clock_sec"].median()
                    oh.append({"instance": inst, "arm": arm, "overhead_ratio": it_b0 / it_arm if it_arm > 0 else np.nan})
        lines.append("## Overhead ratio (B0 iterations/sec divided by arm iterations/sec)\n")
        lines.append(pd.DataFrame(oh).round(3).to_markdown(index=False))
    text = "\n".join(lines)
    (out / "summary.md").write_text(text)
    print(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jar", required=True)
    ap.add_argument("--config", action="append", default=[])
    ap.add_argument("--instances", nargs="+", required=True)
    ap.add_argument("--arms", nargs="+", default=["B0", "B1", "B2", "L", "R"])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--seed-start", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=None, help="wall-clock budget in seconds (primary)")
    ap.add_argument("--max-committed", type=int, default=None, help="committed-neighbourhood budget (secondary)")
    ap.add_argument("--weight", type=float, default=None, help="student-conflict weight for B1/B2/L/R (from weight_sweep)")
    ap.add_argument("--onnx", default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--set", action="append", default=[], help="extra solver property Key=Value passed to every run")
    ap.add_argument("--out", default="runs/bakeoff")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--java", default="java")
    ap.add_argument("--reference", default="B1")
    ap.add_argument("--claim", default="R")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(inst, arm, seed) for inst in args.instances for arm in args.arms for seed in range(args.seed_start, args.seed_start + args.seeds)]
    results = []
    if not args.summary_only:
        with cf.ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(run_one, args.jar, args.config, inst, arm, seed, out, args.timeout, args.max_committed, args.weight, args.onnx, args.java, args.set, args.k): (inst, arm, seed) for inst, arm, seed in jobs}
            for fut in cf.as_completed(futs):
                m = fut.result()
                if m is not None:
                    results.append(flatten(m))
                    r = results[-1]
                    print(f"[bakeoff] {r['instance']} {r['arm']} seed={r['seed']} C={r['C']:.4f} assigned={r['assigned_ratio']:.3f} hard={r['hard']} wall={r['wall_clock_sec']:.0f}s")
    else:
        for inst, arm, seed in jobs:
            mfile = out / Path(inst).stem / arm / f"seed{seed}" / "metrics.json"
            if mfile.exists():
                results.append(flatten(json.loads(mfile.read_text())))
    if not results:
        raise SystemExit("no results")
    df = pd.DataFrame(results).sort_values(["instance", "arm", "seed"])
    df.to_csv(out / "results.csv", index=False)
    summarise(df, out, reference=args.reference, claim=args.claim)


if __name__ == "__main__":
    main()
