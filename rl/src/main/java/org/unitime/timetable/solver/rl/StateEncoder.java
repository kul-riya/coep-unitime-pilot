package org.unitime.timetable.solver.rl;

/**
 * Fixed 48-dimensional state vector. Every coordinate is a rate, fraction, normalised penalty or
 * one-hot, so a policy trained on one term is meaningful on another. Feature order is frozen;
 * {@link #NAMES} is exported to Python for sanity checks.
 */
public final class StateEncoder {
    public static final int DIM = 48;

    public static final String[] NAMES = {
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
        "norm_too_big_rooms", "norm_useless_half_hours", "norm_back_to_back", "norm_broken_time_patterns"
    };

    /** Search-dynamics inputs that are not part of {@link SearchMetrics}. */
    public static final class Dynamics {
        public double bestC = Double.NaN;      // best violation rate seen in this run
        public double previousC = Double.NaN;  // violation rate at the previous macro-step boundary
        public double progress;                // t / T in [0,1]
        public double acceptanceRate;          // accepted / proposals over the last macro-step
        public double idleFraction;            // iterations that committed nothing / K
        public double nullFraction;            // delegate calls that returned null / proposals
        public int previousAction = -1;
        public double churn;                   // lectures whose placement changed in the last macro-step / n
    }

    private static float clip01(double v) { return (float) Math.max(0.0, Math.min(1.0, v)); }
    private static float clip(double v, double lo, double hi) { return (float) Math.max(lo, Math.min(hi, v)); }
    private static float norm(double v, double scale, double clipTo) { return (float) Math.max(0.0, Math.min(clipTo, v / scale)); }

    public static float[] encode(SearchMetrics m, SearchMetrics.Scales s, Dynamics d, RlConfig cfg) {
        float[] x = new float[DIM];
        ConflictReport r = m.conflicts;
        int i = 0;
        double c = r.studentViolationRate();
        x[i++] = clip01(c);
        x[i++] = clip01(r.pairViolationRate());
        x[i++] = clip01(r.intensity / 4.0);
        x[i++] = clip01(r.concentration);
        for (int b = 0; b < ConflictReport.SLOT_BINS; b++) x[i++] = clip01(r.slotProfile[b]);
        x[i++] = clip(Double.isNaN(d.bestC) ? 0.0 : c - d.bestC, -1, 1);
        x[i++] = clip(Double.isNaN(d.previousC) ? 0.0 : c - d.previousC, -1, 1);

        x[i++] = clip01(m.assignedRatio);
        x[i++] = clip01(m.unassignedFraction);
        x[i++] = clip01(Math.min(m.hardViolations, 10) / 10.0);
        x[i++] = norm(Math.abs(m.totalValue), s.total, cfg.oClip);
        x[i++] = norm(m.timePref, s.time, cfg.oClip);
        x[i++] = norm(m.roomPref, s.room, cfg.oClip);
        x[i++] = norm(m.distPref, s.dist, cfg.oClip);
        x[i++] = norm(m.studentConflict, s.studentConflict, cfg.oClip);
        x[i++] = clip01(m.roomUtilMean);
        x[i++] = clip01(m.roomUtilMax);
        x[i++] = clip01(m.roomUtilStd);
        x[i++] = clip01(m.instrUtilMean);
        x[i++] = clip01(m.instrUtilMax);

        x[i++] = clip01(d.progress);
        x[i++] = clip01(d.acceptanceRate);
        x[i++] = clip01(d.idleFraction);
        x[i++] = clip01(d.nullFraction);

        for (int a = 0; a < Operators.COUNT; a++) x[i++] = (d.previousAction == a ? 1f : 0f);

        x[i++] = clip01(d.churn);
        x[i++] = clip01(m.nrVariables == 0 ? 0.0 : (double) r.lecturesInConflict / m.nrVariables);
        x[i++] = clip01(r.conflictedStudents == 0 ? 0.0 : (double) r.violatedStudentPairs / r.conflictedStudents / 4.0);
        x[i++] = norm(m.tooBigRooms, s.tooBigRooms, cfg.oClip);
        x[i++] = norm(m.uselessHalfHours, s.uselessHalfHours, cfg.oClip);
        x[i++] = norm(m.backToBack, s.backToBack, cfg.oClip);
        x[i++] = norm(m.brokenTimePatterns, s.brokenTimePatterns, cfg.oClip);
        if (i != DIM) throw new IllegalStateException("StateEncoder produced " + i + " features, expected " + DIM);
        return x;
    }
}
