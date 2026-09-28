"""Serve a torch policy over gRPC for Java's GrpcPolicy (Rl.Policy=grpc, Rl.Grpc.Target=host:port).

    python -m unitime_rl.serve_policy --ppo models/ppo/maskable_ppo.zip --port 50052
"""
from __future__ import annotations

import argparse
from concurrent import futures

import grpc
import numpy as np
import torch

from .policy_net import PolicyNet, policy_net_from_sb3
from .proto import solver_env_pb2 as pb
from .proto import solver_env_pb2_grpc as pb_grpc


class PolicyServicer(pb_grpc.PolicyServicer):
    def __init__(self, net: PolicyNet, stochastic: bool = False, seed: int = 0):
        self.net = net.eval()
        self.stochastic = stochastic
        self.rng = np.random.default_rng(seed)

    def Act(self, request, context):
        obs = torch.tensor(np.asarray(request.features, dtype=np.float32)).unsqueeze(0)
        mask = np.asarray(request.action_mask, dtype=bool)
        with torch.no_grad():
            logits = self.net(obs)[0].numpy()
        if mask.shape[0] == logits.shape[0]:
            logits = np.where(mask, logits, -1e9)
        if self.stochastic:
            p = np.exp(logits - logits.max())
            p /= p.sum()
            action = int(self.rng.choice(len(p), p=p))
        else:
            action = int(np.argmax(logits))
        return pb.Action(action=action)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ppo")
    g.add_argument("--bc")
    ap.add_argument("--port", type=int, default=50052)
    ap.add_argument("--stochastic", action="store_true")
    args = ap.parse_args(argv)
    if args.ppo:
        from sb3_contrib import MaskablePPO
        net = policy_net_from_sb3(MaskablePPO.load(args.ppo, device="cpu").policy)
    else:
        net = PolicyNet()
        net.load_state_dict(torch.load(args.bc, map_location="cpu")["state_dict"])
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    pb_grpc.add_PolicyServicer_to_server(PolicyServicer(net, args.stochastic), server)
    server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    print(f"Policy service on port {args.port}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
