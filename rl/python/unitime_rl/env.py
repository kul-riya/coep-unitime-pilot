"""Gymnasium environment over the Java SolverEnv gRPC service.

One environment = one Java EnvServer (one resident TimetableModel). An episode is one solve from the
stored initial solution. Actions are operator ids (Discrete(8)); ``action_masks()`` exposes the
invalid-action mask for sb3-contrib's MaskablePPO.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Sequence

import grpc
import gymnasium as gym
import numpy as np

from . import N_ACTIONS, OBS_DIM
from .proto import solver_env_pb2 as pb
from .proto import solver_env_pb2_grpc as pb_grpc


def metrics_to_dict(m: pb.Metrics) -> dict[str, Any]:
    d = {
        "student_violation_rate": m.student_violation_rate,
        "checker_violation_rate": m.checker_violation_rate,
        "pair_violation_rate": m.pair_violation_rate,
        "assigned_ratio": m.assigned_ratio,
        "hard_violations": m.hard_violations,
        "soft_penalty": m.soft_penalty,
        "soft_penalty_norm": m.soft_penalty_norm,
        "total_value": m.total_value,
        "potential": m.potential,
        "iteration": m.iteration,
        "macro_step": m.macro_step,
        "time_sec": m.time_sec,
        "committed": m.committed,
    }
    d.update(dict(m.extra))
    return d


class UniTimeSolverEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        target: str = "localhost:50051",
        instances: Sequence[str] = (),
        properties: dict[str, str] | None = None,
        rpc_timeout_s: float = 3600.0,
        seed_base: int | None = None,
    ):
        super().__init__()
        self.target = target
        self.instances = list(instances)
        self.properties = dict(properties or {})
        self.rpc_timeout_s = rpc_timeout_s
        self._instance_cycle = itertools.cycle(self.instances) if self.instances else None
        self._rng = random.Random(seed_base)
        self.observation_space = gym.spaces.Box(low=-1.0, high=3.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(N_ACTIONS)
        self._channel = grpc.insecure_channel(target)
        self._stub = pb_grpc.SolverEnvStub(self._channel)
        self._mask = np.ones(N_ACTIONS, dtype=bool)
        self.last_info: dict[str, Any] = {}
        self.start_assigned_ratio: float | None = None
        self.current_instance: str | None = None

    # -- gym API -------------------------------------------------------------------------------
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        options = options or {}
        instance = options.get("instance")
        if instance is None and self._instance_cycle is not None:
            instance = next(self._instance_cycle)
        if instance is None:
            instance = self.current_instance or ""
        props = dict(self.properties)
        props.update(options.get("properties", {}))
        solver_seed = seed if seed is not None else self._rng.randrange(1, 2**31 - 1)
        req = pb.InstanceId(instance=instance, seed=solver_seed, properties=props)
        obs_msg = self._stub.Reset(req, timeout=self.rpc_timeout_s)
        self.current_instance = instance
        obs, info = self._unpack(obs_msg)
        self.start_assigned_ratio = info.get("assigned_ratio")
        info["instance"] = instance
        info["solver_seed"] = solver_seed
        self.last_info = info
        return obs, info

    def step(self, action):
        res = self._stub.Step(pb.Action(action=int(action)), timeout=self.rpc_timeout_s)
        obs, info = self._unpack(res.observation)
        info["instance"] = self.current_instance
        info["start_assigned_ratio"] = self.start_assigned_ratio
        if self.start_assigned_ratio is not None and "assigned_ratio" in info:
            info["assigned_drop"] = self.start_assigned_ratio - info["assigned_ratio"]
        # server-side string annotations must not clobber the numeric metrics
        for k, v in res.info.items():
            info.setdefault(k, v)
        self.last_info = info
        return obs, float(res.reward), bool(res.terminated), bool(res.truncated), info

    def action_masks(self) -> np.ndarray:
        return self._mask.copy()

    def close(self):
        try:
            self._stub.Close(pb.Empty(), timeout=30)
        except grpc.RpcError:
            pass
        self._channel.close()

    # -- helpers -------------------------------------------------------------------------------
    def save(self, path: str) -> None:
        self._stub.Save(pb.SavePath(path=path), timeout=120)

    def _unpack(self, obs_msg: pb.Observation):
        obs = np.asarray(obs_msg.features, dtype=np.float32)
        if obs.shape[0] != OBS_DIM:
            raise RuntimeError(f"server returned {obs.shape[0]} features, expected {OBS_DIM}")
        mask = np.asarray(obs_msg.action_mask, dtype=bool)
        if mask.shape[0] == N_ACTIONS:
            self._mask = mask
        else:
            self._mask = np.ones(N_ACTIONS, dtype=bool)
        info = metrics_to_dict(obs_msg.metrics)
        info["action_mask"] = self._mask.copy()
        return obs, info


def make_env(target: str, instances: Sequence[str], properties: dict[str, str] | None, seed_base: int):
    """Factory for SubprocVecEnv (one gRPC channel per subprocess)."""

    def _thunk():
        return UniTimeSolverEnv(target=target, instances=instances, properties=properties, seed_base=seed_base)

    return _thunk
