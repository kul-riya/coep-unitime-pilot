"""Smoke test against a running Java EnvServer.

Start one first, e.g.
    java -cp ../target/unitime-rl-0.1.0-SNAPSHOT-all.jar org.unitime.timetable.solver.rl.EnvServer \
        --port 50051 --instances ../instances --config ../config/unitime-coep-default.properties \
        --set Termination.TimeOut=20 --set Rl.MaxMacroSteps=30
then
    UNITIME_RL_TARGET=localhost:50051 UNITIME_RL_INSTANCE=synthetic-hard .venv/bin/pytest -q tests
"""
import os

import numpy as np
import pytest

from unitime_rl import N_ACTIONS, OBS_DIM
from unitime_rl.env import UniTimeSolverEnv

TARGET = os.environ.get("UNITIME_RL_TARGET")
INSTANCE = os.environ.get("UNITIME_RL_INSTANCE", "synthetic-hard")

pytestmark = pytest.mark.skipif(TARGET is None, reason="set UNITIME_RL_TARGET to a running EnvServer")


def test_reset_step_episode():
    env = UniTimeSolverEnv(target=TARGET, instances=[INSTANCE])
    obs, info = env.reset(seed=1)
    assert obs.shape == (OBS_DIM,)
    assert np.all(np.isfinite(obs))
    assert env.action_masks().shape == (N_ACTIONS,)
    total = 0.0
    steps = 0
    done = False
    rng = np.random.default_rng(0)
    while not done and steps < 500:
        mask = env.action_masks()
        allowed = np.flatnonzero(mask)
        a = int(rng.choice(allowed))
        obs, r, term, trunc, info = env.step(a)
        assert obs.shape == (OBS_DIM,)
        total += r
        steps += 1
        done = term or trunc
    assert done, "episode did not end"
    assert steps > 1
    assert "student_violation_rate" in info
    # potential-based shaping telescopes: the sum of rewards equals Phi(final) - Phi(start) minus step penalties
    assert np.isfinite(total)
    env.close()


def test_two_episodes_reset_restores_start():
    env = UniTimeSolverEnv(target=TARGET, instances=[INSTANCE])
    _, info1 = env.reset(seed=3)
    for _ in range(5):
        env.step(0)
    _, info2 = env.reset(seed=3)
    assert abs(info1["assigned_ratio"] - info2["assigned_ratio"]) < 1e-9
    assert abs(info1["student_violation_rate"] - info2["student_violation_rate"]) < 1e-9
    env.close()
