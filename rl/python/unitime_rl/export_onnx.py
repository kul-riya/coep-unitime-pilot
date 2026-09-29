"""Export the actor of a trained MaskablePPO (or a BC checkpoint) to ONNX for in-JVM inference.

    python -m unitime_rl.export_onnx --ppo models/ppo/maskable_ppo.zip --out models/policy.onnx
    python -m unitime_rl.export_onnx --bc models/bc_policy.pt --out models/bc_policy.onnx

The graph takes ``obs`` [batch, 48] float32 and returns ``logits`` [batch, 8]. Java applies the mask
and the argmax (OnnxPolicy). The export is verified against torch with onnxruntime.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from . import OBS_DIM
from .policy_net import PolicyNet, policy_net_from_sb3


def load_net(args) -> PolicyNet:
    if args.ppo:
        from sb3_contrib import MaskablePPO
        model = MaskablePPO.load(args.ppo, device="cpu")
        return policy_net_from_sb3(model.policy)
    ckpt = torch.load(args.bc, map_location="cpu")
    net = PolicyNet()
    net.load_state_dict(ckpt["state_dict"])
    return net


def export(net: PolicyNet, out: Path, opset: int = 17) -> None:
    net.eval()
    dummy = torch.zeros(1, OBS_DIM, dtype=torch.float32)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        net, dummy, str(out), input_names=["obs"], output_names=["logits"],
        dynamic_axes={"obs": {0: "batch"}, "logits": {0: "batch"}}, opset_version=opset, dynamo=False,
    )


def verify(net: PolicyNet, out: Path, n: int = 64, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 3, size=(n, OBS_DIM)).astype(np.float32)
    with torch.no_grad():
        ref = net(torch.from_numpy(x)).numpy()
    sess = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    got = sess.run(["logits"], {"obs": x})[0]
    return float(np.max(np.abs(ref - got)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ppo", help="MaskablePPO zip")
    g.add_argument("--bc", help="behaviour-cloning checkpoint (.pt)")
    ap.add_argument("--out", default="models/policy.onnx")
    ap.add_argument("--opset", type=int, default=17)
    args = ap.parse_args(argv)
    net = load_net(args)
    out = Path(args.out)
    export(net, out, args.opset)
    err = verify(net, out)
    print(f"exported {out}; max |torch - onnxruntime| = {err:.3e}")
    if err > 1e-4:
        raise SystemExit("ONNX export does not match the torch network")


if __name__ == "__main__":
    main()
