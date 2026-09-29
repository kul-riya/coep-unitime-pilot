package org.unitime.timetable.solver.rl;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import org.cpsolver.coursett.Constants;
import org.cpsolver.coursett.constraint.InstructorConstraint;
import org.cpsolver.coursett.constraint.RoomConstraint;
import org.cpsolver.coursett.criteria.BackToBackInstructorPreferences;
import org.cpsolver.coursett.criteria.BrokenTimePatterns;
import org.cpsolver.coursett.criteria.DistributionPreferences;
import org.cpsolver.coursett.criteria.RoomPreferences;
import org.cpsolver.coursett.criteria.StudentConflict;
import org.cpsolver.coursett.criteria.StudentHardConflict;
import org.cpsolver.coursett.criteria.TimePreferences;
import org.cpsolver.coursett.criteria.TooBigRooms;
import org.cpsolver.coursett.criteria.UselessHalfHours;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.RoomLocation;
import org.cpsolver.coursett.model.TimeLocation;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.criteria.Criterion;

/**
 * Everything the reward and the state vector need about one assignment, read off the model's
 * criteria plus one {@link ConflictReport}. Criterion values are raw (unweighted); the normalised
 * versions divide by {@code Rl.Scale.*} (frozen from baseline runs, see HeadlessSolve --write-scales).
 */
public class SearchMetrics {
    public ConflictReport conflicts;
    public int nrVariables, nrAssigned;
    public double assignedRatio, unassignedFraction;
    public int hardViolations;
    public double timePref, roomPref, distPref, studentConflict, hardStudentConflict;
    public double tooBigRooms, uselessHalfHours, backToBack, brokenTimePatterns;
    public double totalValue;
    /** raw time + room + distribution penalty */
    public double softPenalty;
    /** softPenalty / Rl.Scale.O, clipped to [0, Rl.OClip] */
    public double softPenaltyNorm;
    public double roomUtilMean, roomUtilMax, roomUtilStd, instrUtilMean, instrUtilMax;
    public long iteration;
    public double timeSec;
    public double potential;

    public double studentViolationRate() { return conflicts.studentViolationRate(); }

    /** Phi(s) = -wC*C - wU*U - wH*H - wO*O */
    public static double potential(RlConfig cfg, double c, double u, int h, double oNorm) {
        return -cfg.wC * c - cfg.wU * u - cfg.wH * h - cfg.wO * oNorm;
    }

    /**
     * Weighted objective. Before the solver has started, the Perturbations criterion has no
     * perturbations counter yet and throws; fall back to summing the criteria that can be evaluated.
     */
    public static double safeTotalValue(TimetableModel model, Assignment<Lecture, Placement> assignment) {
        try {
            return model.getTotalValue(assignment);
        } catch (RuntimeException e) {
            double total = 0;
            for (Criterion<Lecture, Placement> c: model.getCriteria()) {
                try { total += c.getWeightedValue(assignment); } catch (RuntimeException ignore) { /* not initialised yet */ }
            }
            return total;
        }
    }

    private static double value(TimetableModel model, Class<? extends Criterion<Lecture, Placement>> clazz, Assignment<Lecture, Placement> assignment) {
        Criterion<Lecture, Placement> c = model.getCriterion(clazz);
        return c == null ? 0.0 : c.getValue(assignment);
    }

    /**
     * @param computeHard run the O(n * constraints) hard-violation scan (once per macro-step, not per iteration)
     */
    public static SearchMetrics compute(TimetableModel model, Assignment<Lecture, Placement> assignment, ConflictReport report,
            RlConfig cfg, Scales scales, boolean computeHard, long iteration, double timeSec) {
        SearchMetrics m = new SearchMetrics();
        m.conflicts = report;
        m.iteration = iteration;
        m.timeSec = timeSec;
        m.nrVariables = model.variables().size();
        m.nrAssigned = assignment.nrAssignedVariables();
        m.assignedRatio = m.nrVariables == 0 ? 1.0 : (double) m.nrAssigned / m.nrVariables;
        m.unassignedFraction = 1.0 - m.assignedRatio;
        m.timePref = value(model, TimePreferences.class, assignment);
        m.roomPref = value(model, RoomPreferences.class, assignment);
        m.distPref = value(model, DistributionPreferences.class, assignment);
        m.studentConflict = value(model, StudentConflict.class, assignment);
        m.hardStudentConflict = value(model, StudentHardConflict.class, assignment);
        m.tooBigRooms = value(model, TooBigRooms.class, assignment);
        m.uselessHalfHours = value(model, UselessHalfHours.class, assignment);
        m.backToBack = value(model, BackToBackInstructorPreferences.class, assignment);
        m.brokenTimePatterns = value(model, BrokenTimePatterns.class, assignment);
        m.totalValue = safeTotalValue(model, assignment);
        m.softPenalty = m.timePref + m.roomPref + m.distPref;
        scales.freezeIfNeeded(m);
        m.softPenaltyNorm = Math.max(0.0, Math.min(cfg.oClip, m.softPenalty / scales.o));
        m.hardViolations = computeHard ? countHardViolations(model, assignment) : 0;
        utilisation(model, assignment, m);
        m.potential = potential(cfg, m.studentViolationRate(), m.unassignedFraction, m.hardViolations, m.softPenaltyNorm);
        return m;
    }

    /**
     * Assigned placements that are invalid or in conflict with another assigned placement under a hard
     * constraint. Zero whenever Basic.DisobeyHard is false, but computed so a non-zero value is visible.
     */
    public static int countHardViolations(TimetableModel model, Assignment<Lecture, Placement> assignment) {
        int violations = 0;
        for (Lecture lecture: model.variables()) {
            Placement p = assignment.getValue(lecture);
            if (p == null) continue;
            if (!p.isValid()) { violations++; continue; }
            Set<Placement> conflicts = model.conflictValues(assignment, p);
            for (Placement c: conflicts) {
                if (!c.variable().equals(lecture)) { violations++; break; }
            }
        }
        return violations;
    }

    private static void utilisation(TimetableModel model, Assignment<Lecture, Placement> assignment, SearchMetrics m) {
        int firstDaySlot = model.getProperties().getPropertyInt("General.FirstDaySlot", Constants.DAY_SLOTS_FIRST);
        int lastDaySlot = model.getProperties().getPropertyInt("General.LastDaySlot", Constants.DAY_SLOTS_LAST);
        int firstWorkDay = model.getProperties().getPropertyInt("General.FirstWorkDay", 0);
        int lastWorkDay = model.getProperties().getPropertyInt("General.LastWorkDay", Constants.NR_DAYS_WEEK - 1);
        double capacity = Math.max(1, (lastDaySlot - firstDaySlot + 1)) * Math.max(1, (lastWorkDay - firstWorkDay + 1));
        Map<Long, Double> rooms = new HashMap<Long, Double>();
        for (RoomConstraint rc: model.getRoomConstraints()) rooms.put(rc.getResourceId(), 0.0);
        Map<Long, Double> instructors = new HashMap<Long, Double>();
        for (InstructorConstraint ic: model.getInstructorConstraints()) instructors.put(ic.getResourceId(), 0.0);
        for (Lecture lecture: model.variables()) {
            Placement p = assignment.getValue(lecture);
            if (p == null) continue;
            TimeLocation t = p.getTimeLocation();
            double slots = (double) t.getNrSlotsPerMeeting() * Integer.bitCount(t.getDayCode());
            if (p.getRoomLocations() != null)
                for (RoomLocation rl: p.getRoomLocations())
                    if (rooms.containsKey(rl.getId())) rooms.merge(rl.getId(), slots, Double::sum);
            for (InstructorConstraint ic: lecture.getInstructorConstraints())
                instructors.merge(ic.getResourceId(), slots, Double::sum);
        }
        double[] r = moments(rooms.values(), capacity);
        m.roomUtilMean = r[0]; m.roomUtilMax = r[1]; m.roomUtilStd = r[2];
        double[] i = moments(instructors.values(), capacity);
        m.instrUtilMean = i[0]; m.instrUtilMax = i[1];
    }

    private static double[] moments(Iterable<Double> values, double capacity) {
        int n = 0; double sum = 0, max = 0, sq = 0;
        for (double v: values) {
            double u = Math.min(1.0, v / capacity);
            n++; sum += u; sq += u * u; max = Math.max(max, u);
        }
        if (n == 0) return new double[] {0, 0, 0};
        double mean = sum / n;
        return new double[] {mean, max, Math.sqrt(Math.max(0, sq / n - mean * mean))};
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new LinkedHashMap<String, Object>();
        map.put("student_violation_rate", conflicts.studentViolationRate());
        map.put("checker_violation_rate", conflicts.checkerViolationRate());
        map.put("pair_violation_rate", conflicts.pairViolationRate());
        map.put("zero_conflict_fraction", conflicts.zeroConflictFraction());
        map.put("conflicted_students", conflicts.conflictedStudents);
        map.put("students_two_plus", conflicts.studentsWithTwoPlus);
        map.put("students_total", conflicts.studentsTotal);
        map.put("violated_student_pairs", conflicts.violatedStudentPairs);
        map.put("pairs_violated", conflicts.pairsViolated);
        map.put("pairs_total", conflicts.pairsTotal);
        map.put("intensity", conflicts.intensity);
        map.put("concentration", conflicts.concentration);
        map.put("nr_variables", nrVariables);
        map.put("nr_assigned", nrAssigned);
        map.put("assigned_ratio", assignedRatio);
        map.put("hard_violations", hardViolations);
        map.put("time_pref", timePref);
        map.put("room_pref", roomPref);
        map.put("dist_pref", distPref);
        map.put("student_conflict_criterion", studentConflict);
        map.put("hard_student_conflict_criterion", hardStudentConflict);
        map.put("too_big_rooms", tooBigRooms);
        map.put("useless_half_hours", uselessHalfHours);
        map.put("back_to_back_instructor", backToBack);
        map.put("broken_time_patterns", brokenTimePatterns);
        map.put("total_value", totalValue);
        map.put("soft_penalty", softPenalty);
        map.put("soft_penalty_norm", softPenaltyNorm);
        map.put("room_util_mean", roomUtilMean);
        map.put("room_util_max", roomUtilMax);
        map.put("room_util_std", roomUtilStd);
        map.put("instr_util_mean", instrUtilMean);
        map.put("instr_util_max", instrUtilMax);
        map.put("iteration", iteration);
        map.put("time_sec", timeSec);
        map.put("potential", potential);
        return map;
    }

    /** Normalisation scales, frozen either from Rl.Scale.* or from the first observed metrics. */
    public static class Scales {
        private final RlConfig cfg;
        public double o = 1, total = 1, time = 1, room = 1, dist = 1, studentConflict = 1, tooBigRooms = 1, uselessHalfHours = 1, backToBack = 1, brokenTimePatterns = 1;
        private boolean frozen = false;

        public Scales(RlConfig cfg) { this.cfg = cfg; }

        private static double pos(double v) { return v > 1e-9 ? v : 1.0; }

        void freezeIfNeeded(SearchMetrics m) {
            if (frozen) return;
            o = cfg.scale("O", pos(m.softPenalty));
            total = cfg.scale("Total", pos(Math.abs(m.totalValue)));
            time = cfg.scale("Time", pos(m.timePref));
            room = cfg.scale("Room", pos(m.roomPref));
            dist = cfg.scale("Dist", pos(m.distPref));
            studentConflict = cfg.scale("StudentConflict", pos(m.studentConflict));
            tooBigRooms = cfg.scale("TooBigRooms", pos(m.tooBigRooms));
            uselessHalfHours = cfg.scale("UselessHalfHours", pos(m.uselessHalfHours));
            backToBack = cfg.scale("BackToBack", pos(m.backToBack));
            brokenTimePatterns = cfg.scale("BrokenTimePatterns", pos(m.brokenTimePatterns));
            frozen = true;
        }

        public Map<String, Double> toMap() {
            Map<String, Double> map = new LinkedHashMap<String, Double>();
            map.put("Rl.Scale.O", o); map.put("Rl.Scale.Total", total); map.put("Rl.Scale.Time", time);
            map.put("Rl.Scale.Room", room); map.put("Rl.Scale.Dist", dist); map.put("Rl.Scale.StudentConflict", studentConflict);
            map.put("Rl.Scale.TooBigRooms", tooBigRooms); map.put("Rl.Scale.UselessHalfHours", uselessHalfHours);
            map.put("Rl.Scale.BackToBack", backToBack); map.put("Rl.Scale.BrokenTimePatterns", brokenTimePatterns);
            return map;
        }
    }
}
