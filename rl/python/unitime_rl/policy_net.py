"""The policy network used everywhere: MLP 48 -> 128 -> 128 -> 8 logits (tanh), matching the actor
branch of sb3-contrib's MaskableActorCriticPolicy with net_arch=dict(pi=[128,128], vf=[128,128]).
"""
from __future__ import annotations

import torch
import torch.nn as nn

from . import N_ACTIONS, OBS_DIM

HIDDEN = (128, 128)


class PolicyNet(nn.Module):
    def __init__(self, obs_dim: int = OBS_DIM, n_actions: int = N_ACTIONS, hidden=HIDDEN):
        super().__init__()
        layers: list[nn.Module] = []
        last = obs_dim
        for h in hidden:
            layers += [nn.Linear(last, h), nn.Tanh()]
            last = h
        self.body = nn.Sequential(*layers)
        self.head = nn.Linear(last, n_actions)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.head(self.body(obs))


def sb3_actor_state_dict(net: PolicyNet) -> dict[str, torch.Tensor]:
    """Map PolicyNet weights onto MaskableActorCriticPolicy keys (mlp_extractor.policy_net.*, action_net.*)."""
    sd = {}
    linear_idx = 0
    for i, layer in enumerate(net.body):
        if isinstance(layer, nn.Linear):
            sd[f"mlp_extractor.policy_net.{linear_idx * 2}.weight"] = layer.weight.detach().clone()
            sd[f"mlp_extractor.policy_net.{linear_idx * 2}.bias"] = layer.bias.detach().clone()
            linear_idx += 1
    sd["action_net.weight"] = net.head.weight.detach().clone()
    sd["action_net.bias"] = net.head.bias.detach().clone()
    return sd


def policy_net_from_sb3(policy) -> PolicyNet:
    """Extract the actor branch of a trained MaskablePPO policy into a standalone PolicyNet."""
    net = PolicyNet()
    sd = policy.state_dict()
    linear_idx = 0
    for layer in net.body:
        if isinstance(layer, nn.Linear):
            layer.weight.data.copy_(sd[f"mlp_extractor.policy_net.{linear_idx * 2}.weight"])
            layer.bias.data.copy_(sd[f"mlp_extractor.policy_net.{linear_idx * 2}.bias"])
            linear_idx += 1
    net.head.weight.data.copy_(sd["action_net.weight"])
    net.head.bias.data.copy_(sd["action_net.bias"])
    return net
