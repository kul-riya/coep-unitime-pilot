"""B1 weight sweep: the control that asks "was the objective just under-weighted?".

Runs arm B1 (stock IFS selector) for each student-conflict weight and seed, then picks the weight
with the lowest held-out violation rate whose assigned ratio is within 1 point of B0 (which must be
present in the same output directory, or is run here with --with-b0). Also reports whether B1 alone
already clears the 25% reduction versus B0, in which case the research question is answered in the
negative and the RL run is optional (execution order, step 2).

    python -m unitime_rl.weight_sweep --jar ../target/unitime-rl-0.1.0-SNAPSHOT-all.jar \
        --config ../config/unitime-coep-default.properties --instances instances/spr2026.xml \
        --weights 0.2 0.5 1 2 5 10 --seeds 5 --timeout 600 --out runs/sweep --with-b0
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
from pathlib import Path

import pandas as pd

from .bakeoff import flatten, run_one


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jar", required=True)
    ap.add_argument("--config", action="append", default=[])
    ap.add_argument("--instances", nargs="+", required=True)
    ap.add_argument("--weights", nargs="+", type=float, default=[0.2, 0.5, 1.0, 2.0, 5.0, 10.0])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--max-committed", type=int, default=None)
    ap.add_argument("--with-b0", action="store_true", help="also run B0 (stock weight) as the reference")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default="runs/sweep")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--java", default="java")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for inst in args.instances:
        for seed in range(1, args.seeds + 1):
            if args.with_b0:
                jobs.append((inst, "B0", None, seed))
            for w in args.weights:
                jobs.append((inst, "B1", w, seed))
    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {}
        for inst, arm, w, seed in jobs:
            sub = out / (f"w{w:g}" if w is not None else "B0")
            futs[ex.submit(run_one, args.jar, args.config, inst, arm, seed, sub, args.timeout, args.max_committed, w, None, args.java, args.set, None)] = (inst, arm, w, seed)
        for fut in cf.as_completed(futs):
            inst, arm, w, seed = futs[fut]
            m = fut.result()
            if m is None:
                continue
            r = flatten(m)
            r["weight"] = w if w is not None else m.get("student_conflict_weight")
            rows.append(r)
            print(f"[sweep] {r['instance']} {arm} w={r['weight']} seed={seed} C={r['C']:.4f} assigned={r['assigned_ratio']:.3f}")
    df = pd.DataFrame(rows)
    df.to_csv(out / "sweep_results.csv", index=False)

    b0 = df[df.arm == "B0"].groupby("instance").agg(C_B0=("C", "median"), assigned_B0=("assigned_ratio", "median"))
    b1 = df[df.arm == "B1"].groupby(["instance", "weight"]).agg(C=("C", "median"), assigned=("assigned_ratio", "median"), soft=("soft_penalty", "median"), n=("seed", "count")).reset_index()
    chosen = {}
    lines = ["## B1 weight sweep (median over seeds)\n", b1.round(4).to_markdown(index=False), ""]
    for inst, grp in b1.groupby("instance"):
        if inst in b0.index:
            ok = grp[grp.assigned >= b0.loc[inst, "assigned_B0"] - 0.01]
            ref_c = b0.loc[inst, "C_B0"]
        else:
            ok = grp
            ref_c = None
        if ok.empty:
            lines.append(f"{inst}: no weight keeps the assigned ratio within 1 point of B0")
            continue
        best = ok.sort_values("C").iloc[0]
        chosen[inst] = float(best["weight"])
        msg = f"{inst}: chosen weight = {best['weight']:g} (C={best['C']:.4f}, assigned={best['assigned']:.4f})"
        if ref_c:
            rel = (ref_c - best["C"]) / ref_c
            msg += f"; reduction vs B0 = {rel:.3f} -> " + ("B1 ALONE CLEARS 25%: research question answered in the negative, RL run optional" if rel >= 0.25 else "B1 does not clear 25%")
        lines.append(msg)
    text = "\n".join(lines)
    (out / "summary.md").write_text(text)
    (out / "b1_weight.json").write_text(json.dumps({"chosen": chosen, "overall": (sorted(chosen.values())[len(chosen) // 2] if chosen else None)}, indent=2))
    print(text)


if __name__ == "__main__":
    main()
