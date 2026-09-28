"""Learned operator selection for the UniTime/CPSolver course timetabling search."""

OBS_DIM = 48
N_ACTIONS = 8

OPERATOR_NAMES = [
    "TimeChange", "RoomChange", "RandomMove", "TimeSwap", "Suggestion", "RandomStudentSwap",
    "ConflictBiasedTimeMove", "ConflictBiasedStudentSwap",
]

# Must match org.unitime.timetable.solver.rl.StateEncoder.NAMES
FEATURE_NAMES = [
    "student_violation_rate", "pair_violation_rate", "intensity", "concentration",
    "slot_bin_0", "slot_bin_1", "slot_bin_2", "slot_bin_3", "slot_bin_4",
    "slot_bin_5", "slot_bin_6", "slot_bin_7", "slot_bin_8", "slot_bin_9",
    "improvement_gap", "recent_slope",
    "assigned_ratio", "unassigned_fraction", "hard_violations", "norm_total",
    "norm_time_pref", "norm_room_pref", "norm_dist_pref", "norm_student_conflict",
    "room_util_mean", "room_util_max", "room_util_std", "instr_util_mean", "instr_util_max",
    "progress", "acceptance_rate", "idle_fraction", "null_fraction",
    "prev_op_0", "prev_op_1", "prev_op_2", "prev_op_3", "prev_op_4", "prev_op_5", "prev_op_6", "prev_op_7",
    "churn", "lectures_in_conflict_share", "pairs_per_conflicted_student",
    "norm_too_big_rooms", "norm_useless_half_hours", "norm_back_to_back", "norm_broken_time_patterns",
]
assert len(FEATURE_NAMES) == OBS_DIM
