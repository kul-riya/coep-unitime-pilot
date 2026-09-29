from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class InstanceId(_message.Message):
    __slots__ = ("instance", "seed", "properties")
    class PropertiesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    INSTANCE_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    instance: str
    seed: int
    properties: _containers.ScalarMap[str, str]
    def __init__(self, instance: _Optional[str] = ..., seed: _Optional[int] = ..., properties: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Metrics(_message.Message):
    __slots__ = ("student_violation_rate", "checker_violation_rate", "pair_violation_rate", "assigned_ratio", "hard_violations", "soft_penalty", "soft_penalty_norm", "total_value", "potential", "iteration", "macro_step", "time_sec", "committed", "extra")
    class ExtraEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    STUDENT_VIOLATION_RATE_FIELD_NUMBER: _ClassVar[int]
    CHECKER_VIOLATION_RATE_FIELD_NUMBER: _ClassVar[int]
    PAIR_VIOLATION_RATE_FIELD_NUMBER: _ClassVar[int]
    ASSIGNED_RATIO_FIELD_NUMBER: _ClassVar[int]
    HARD_VIOLATIONS_FIELD_NUMBER: _ClassVar[int]
    SOFT_PENALTY_FIELD_NUMBER: _ClassVar[int]
    SOFT_PENALTY_NORM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    POTENTIAL_FIELD_NUMBER: _ClassVar[int]
    ITERATION_FIELD_NUMBER: _ClassVar[int]
    MACRO_STEP_FIELD_NUMBER: _ClassVar[int]
    TIME_SEC_FIELD_NUMBER: _ClassVar[int]
    COMMITTED_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    student_violation_rate: float
    checker_violation_rate: float
    pair_violation_rate: float
    assigned_ratio: float
    hard_violations: int
    soft_penalty: float
    soft_penalty_norm: float
    total_value: float
    potential: float
    iteration: int
    macro_step: int
    time_sec: float
    committed: int
    extra: _containers.ScalarMap[str, float]
    def __init__(self, student_violation_rate: _Optional[float] = ..., checker_violation_rate: _Optional[float] = ..., pair_violation_rate: _Optional[float] = ..., assigned_ratio: _Optional[float] = ..., hard_violations: _Optional[int] = ..., soft_penalty: _Optional[float] = ..., soft_penalty_norm: _Optional[float] = ..., total_value: _Optional[float] = ..., potential: _Optional[float] = ..., iteration: _Optional[int] = ..., macro_step: _Optional[int] = ..., time_sec: _Optional[float] = ..., committed: _Optional[int] = ..., extra: _Optional[_Mapping[str, float]] = ...) -> None: ...

class Observation(_message.Message):
    __slots__ = ("features", "action_mask", "metrics")
    FEATURES_FIELD_NUMBER: _ClassVar[int]
    ACTION_MASK_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    features: _containers.RepeatedScalarFieldContainer[float]
    action_mask: _containers.RepeatedScalarFieldContainer[bool]
    metrics: Metrics
    def __init__(self, features: _Optional[_Iterable[float]] = ..., action_mask: _Optional[_Iterable[bool]] = ..., metrics: _Optional[_Union[Metrics, _Mapping]] = ...) -> None: ...

class Action(_message.Message):
    __slots__ = ("action",)
    ACTION_FIELD_NUMBER: _ClassVar[int]
    action: int
    def __init__(self, action: _Optional[int] = ...) -> None: ...

class StepResult(_message.Message):
    __slots__ = ("observation", "reward", "terminated", "truncated", "info")
    class InfoEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    OBSERVATION_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    TERMINATED_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    observation: Observation
    reward: float
    terminated: bool
    truncated: bool
    info: _containers.ScalarMap[str, str]
    def __init__(self, observation: _Optional[_Union[Observation, _Mapping]] = ..., reward: _Optional[float] = ..., terminated: _Optional[bool] = ..., truncated: _Optional[bool] = ..., info: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SavePath(_message.Message):
    __slots__ = ("path",)
    PATH_FIELD_NUMBER: _ClassVar[int]
    path: str
    def __init__(self, path: _Optional[str] = ...) -> None: ...
