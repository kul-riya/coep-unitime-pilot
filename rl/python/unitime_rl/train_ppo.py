"""Maskable PPO over the eight operators, warm-started from behaviour cloning.

    # start N Java workers first, e.g. ports 50051..50054
    python -m unitime_rl.train_ppo --targets localhost:50051 localhost:50052 \
        --instances spr2025 spr2026 --bc-init models/bc_policy.pt --timesteps 200000 --out models/ppo

Discount gamma = 1 (finite episode, telescoping potential). Episodes whose final assigned ratio is
more than 5 points below the start are excluded from the policy gradient (their advantages are
zeroed in the rollout buffer) and logged as a diagnostic, per the research document.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from . import N_ACTIONS
from .env import UniTimeSolverEnv
from .policy_net import PolicyNet, sb3_actor_state_dict


def mask_fn(env: UniTimeSolverEnv):
    return env.action_masks()


def make_thunk(target, instances, properties, seed_base):
    def _thunk():
        env = UniTimeSolverEnv(target=target, instances=instances, properties=properties, seed_base=seed_base)
        return ActionMasker(env, mask_fn)
    return _thunk


class UnassignDiscardCallback(BaseCallback):
    """Zero the advantages of episodes that ended with assigned ratio > `max_drop` below the start."""

    def __init__(self, max_drop: float = 0.05, log_path: Path | None = None, verbose: int = 0):
        super().__init__(verbose)
        self.max_drop = max_drop
        self.log_path = log_path
        self._episode_start = None  # per env: buffer position where the current episode started
        self.discarded_episodes = 0
        self.total_episodes = 0
        self._pending = []  # (env_idx, start_pos, end_pos)

    def _on_rollout_start(self) -> None:
        n = self.training_env.num_envs
        self._episode_start = [0] * n
        self._pending = []

    def _on_step(self) -> bool:
        dones = self.locals["dones"]
        infos = self.locals["infos"]
        pos = self.model.rollout_buffer.pos  # position *after* this step was added
        for i, done in enumerate(dones):
            if not done:
                continue
            self.total_episodes += 1
            drop = infos[i].get("assigned_drop")
            if drop is not None and drop > self.max_drop:
                self.discarded_episodes += 1
                self._pending.append((i, self._episode_start[i], pos))
                if self.log_path is not None:
                    with open(self.log_path, "a") as fh:
                        fh.write(json.dumps({"t": time.time(), "env": i, "assigned_drop": drop, "info": {k: v for k, v in infos[i].items() if isinstance(v, (int, float, str))}}) + "\n")
            self._episode_start[i] = pos
        return True

    def _on_rollout_end(self) -> None:
        buf = self.model.rollout_buffer
        for env_idx, start, end in self._pending:
            buf.advantages[start:end, env_idx] = 0.0
        if self.verbose and self._pending:
            print(f"[discard] zeroed {len(self._pending)} episode(s) with assigned-ratio drop > {self.max_drop}")
        self.logger.record("rl/discarded_episodes", self.discarded_episodes)
        self.logger.record("rl/total_episodes", self.total_episodes)


class MetricsCallback(BaseCallback):
    def __init__(self):
        super().__init__()
        self.last_c = []

    def _on_step(self) -> bool:
        for i, done in enumerate(self.locals["dones"]):
            if done:
                info = self.locals["infos"][i]
                if "student_violation_rate" in info:
                    self.last_c.append(float(info["student_violation_rate"]))
                    self.logger.record("rl/final_C", float(info["student_violation_rate"]))
                    self.logger.record("rl/final_assigned_ratio", float(info.get("assigned_ratio", float("nan"))))
                    self.logger.record("rl/final_soft_penalty", float(info.get("soft_penalty", float("nan"))))
        return True


def load_bc_into_ppo(model: MaskablePPO, bc_path: str) -> None:
    ckpt = torch.load(bc_path, map_location="cpu")
    net = PolicyNet()
    net.load_state_dict(ckpt["state_dict"])
    actor_sd = sb3_actor_state_dict(net)
    missing, unexpected = model.policy.load_state_dict(actor_sd, strict=False)
    if unexpected:
        raise RuntimeError(f"BC weights have unexpected keys: {unexpected}")
    loaded = [k for k in actor_sd if k not in missing]
    print(f"loaded {len(loaded)} actor tensors from {bc_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets", nargs="+", default=["localhost:50051"], help="one Java EnvServer per parallel environment")
    ap.add_argument("--instances", nargs="*", default=[], help="instance names (files in the server's --instances dir)")
    ap.add_argument("--prop", action="append", default=[], help="solver property override Key=Value (e.g. Comparator.StudentConflictWeight=1.0)")
    ap.add_argument("--bc-init", default=None)
    ap.add_argument("--resume", default=None, help="continue from a saved MaskablePPO zip")
    ap.add_argument("--timesteps", type=int, default=100_000)
    ap.add_argument("--n-steps", type=int, default=256, help="rollout length per environment (macro-steps)")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--ent-coef", type=float, default=0.01)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--gae-lambda", type=float, default=0.95)
    ap.add_argument("--max-assigned-drop", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="models/ppo")
    ap.add_argument("--subproc", action="store_true", help="use SubprocVecEnv so environments step concurrently")
    args = ap.parse_args(argv)

    properties = dict(kv.split("=", 1) for kv in args.prop)
    thunks = [make_thunk(t, args.instances, properties, seed_base=args.seed * 1000 + i) for i, t in enumerate(args.targets)]
    venv = SubprocVecEnv(thunks) if (args.subproc and len(thunks) > 1) else DummyVecEnv(thunks)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    policy_kwargs = dict(net_arch=dict(pi=[128, 128], vf=[128, 128]), activation_fn=torch.nn.Tanh)
    try:
        import tensorboard  # noqa: F401
        tb_log = str(out / "tb")
    except ImportError:
        tb_log = None
    if args.resume:
        model = MaskablePPO.load(args.resume, env=venv, device="cpu")
    else:
        model = MaskablePPO(
            "MlpPolicy", venv, policy_kwargs=policy_kwargs, n_steps=args.n_steps, batch_size=args.batch_size,
            learning_rate=args.lr, ent_coef=args.ent_coef, gamma=args.gamma, gae_lambda=args.gae_lambda,
            seed=args.seed, verbose=1, device="cpu", tensorboard_log=tb_log,
        )
        if args.bc_init:
            load_bc_into_ppo(model, args.bc_init)

    callbacks = [UnassignDiscardCallback(args.max_assigned_drop, log_path=out / "discarded_episodes.jsonl", verbose=1), MetricsCallback()]
    model.learn(total_timesteps=args.timesteps, callback=callbacks, progress_bar=False)
    model.save(out / "maskable_ppo.zip")
    with open(out / "train_args.json", "w") as fh:
        json.dump(vars(args), fh, indent=2)
    print(f"saved {out / 'maskable_ppo.zip'}")
    venv.close()


if __name__ == "__main__":
    main()
