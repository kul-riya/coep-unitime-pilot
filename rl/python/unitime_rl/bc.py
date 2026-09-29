"""Behaviour cloning from shadow-mode trajectories.

Shadow runs (HeadlessSolve --arm SHADOW) write one JSON line per macro-step with the state ``obs``,
the ``mask`` and ``label`` = the operator the default selector effectively used most in that
macro-step. This trains PolicyNet with masked cross-entropy and saves weights that
``train_ppo.py --bc-init`` loads into MaskablePPO.

    python -m unitime_rl.bc --logs runs/shadow/**/trajectory.jsonl --out models/bc_policy.pt
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from . import N_ACTIONS, OBS_DIM
from .policy_net import PolicyNet


def load_shadow_logs(patterns: list[str]):
    obs, masks, labels = [], [], []
    files = [f for p in patterns for f in sorted(glob.glob(p, recursive=True))]
    if not files:
        raise SystemExit(f"no trajectory files match {patterns}")
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("label", -1) is None or rec.get("label", -1) < 0:
                    continue
                if rec.get("label_total", 0) == 0:
                    continue
                o = rec["obs"]
                if o is None or len(o) != OBS_DIM:
                    continue
                obs.append(o)
                m = rec.get("mask") or [True] * N_ACTIONS
                masks.append(m)
                labels.append(int(rec["label"]))
    X = torch.tensor(np.asarray(obs, dtype=np.float32))
    M = torch.tensor(np.asarray(masks, dtype=bool))
    y = torch.tensor(np.asarray(labels, dtype=np.int64))
    return X, M, y, files


def masked_logits(logits: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    return logits.masked_fill(~mask, -1e9)


def train(X, M, y, epochs=30, lr=1e-3, batch_size=256, seed=0, weight_decay=1e-5, val_frac=0.1):
    torch.manual_seed(seed)
    n = X.shape[0]
    perm = torch.randperm(n)
    n_val = int(n * val_frac)
    val_idx, tr_idx = perm[:n_val], perm[n_val:]
    net = PolicyNet()
    opt = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=weight_decay)
    # class weights against label imbalance (the default selector is mostly operator 0/2)
    counts = torch.bincount(y[tr_idx], minlength=N_ACTIONS).float().clamp(min=1)
    weights = (counts.sum() / counts) / N_ACTIONS
    history = []
    for epoch in range(epochs):
        net.train()
        idx = tr_idx[torch.randperm(len(tr_idx))]
        total, correct, loss_sum = 0, 0, 0.0
        for i in range(0, len(idx), batch_size):
            b = idx[i:i + batch_size]
            logits = masked_logits(net(X[b]), M[b])
            loss = F.cross_entropy(logits, y[b], weight=weights)
            opt.zero_grad()
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(b)
            correct += (logits.argmax(1) == y[b]).sum().item()
            total += len(b)
        net.eval()
        with torch.no_grad():
            if n_val > 0:
                vl = masked_logits(net(X[val_idx]), M[val_idx])
                val_acc = (vl.argmax(1) == y[val_idx]).float().mean().item()
            else:
                val_acc = float("nan")
        history.append({"epoch": epoch, "loss": loss_sum / max(1, total), "train_acc": correct / max(1, total), "val_acc": val_acc})
        print(f"epoch {epoch:3d} loss {loss_sum / max(1, total):.4f} train_acc {correct / max(1, total):.3f} val_acc {val_acc:.3f}")
    return net, history


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", nargs="+", required=True, help="glob(s) of trajectory.jsonl files from SHADOW runs")
    ap.add_argument("--out", default="models/bc_policy.pt")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    X, M, y, files = load_shadow_logs(args.logs)
    print(f"{len(files)} files, {X.shape[0]} macro-steps; label histogram: {torch.bincount(y, minlength=N_ACTIONS).tolist()}")
    net, history = train(X, M, y, epochs=args.epochs, lr=args.lr, batch_size=args.batch_size, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": net.state_dict(), "history": history, "n_samples": int(X.shape[0]), "files": files}, out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
