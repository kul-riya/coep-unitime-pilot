"""Offline checks: BC weights load into MaskablePPO's actor and the ONNX export matches torch."""
import tempfile
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO

from unitime_rl import N_ACTIONS, OBS_DIM
from unitime_rl.export_onnx import export, verify
from unitime_rl.policy_net import PolicyNet, policy_net_from_sb3, sb3_actor_state_dict


class _DummyEnv(gym.Env):
    def __init__(self):
        self.observation_space = gym.spaces.Box(low=-1.0, high=3.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = gym.spaces.Discrete(N_ACTIONS)

    def reset(self, *, seed=None, options=None):
        return np.zeros(OBS_DIM, dtype=np.float32), {}

    def step(self, action):
        return np.zeros(OBS_DIM, dtype=np.float32), 0.0, True, False, {}

    def action_masks(self):
        return np.ones(N_ACTIONS, dtype=bool)


def test_bc_weights_load_into_ppo_actor():
    torch.manual_seed(0)
    net = PolicyNet()
    model = MaskablePPO("MlpPolicy", _DummyEnv(), policy_kwargs=dict(net_arch=dict(pi=[128, 128], vf=[128, 128]), activation_fn=torch.nn.Tanh), device="cpu", n_steps=8, batch_size=8)
    sd = sb3_actor_state_dict(net)
    missing, unexpected = model.policy.load_state_dict(sd, strict=False)
    assert not unexpected
    assert all(k not in missing for k in sd)
    x = torch.rand(5, OBS_DIM)
    with torch.no_grad():
        ref = net(x)
        back = policy_net_from_sb3(model.policy)(x)
    assert torch.allclose(ref, back, atol=1e-6)


def test_onnx_export_matches_torch():
    net = PolicyNet()
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "p.onnx"
        export(net, out)
        assert verify(net, out) < 1e-4
