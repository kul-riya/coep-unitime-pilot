package org.unitime.timetable.solver.rl;

import org.cpsolver.coursett.criteria.DistributionPreferences;
import org.cpsolver.coursett.criteria.RoomPreferences;
import org.cpsolver.coursett.criteria.TimePreferences;
import org.cpsolver.coursett.heuristics.TimetableComparator;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.criteria.Criterion;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solution.SolutionComparator;
import org.cpsolver.ifs.util.DataProperties;

/**
 * Incumbent-update rule used during training: fewer unassigned classes, then lower student violation
 * rate C (conflict checker), then lower time + room + distribution penalty O. Hard violations are not
 * a key because Basic.DisobeyHard stays false and every operator uses CPSolver's hard filter.
 *
 * Set with {@code Comparator.Class=org.unitime.timetable.solver.rl.LexicographicComparator}. When no
 * {@link RlRuntime} is registered for the model it behaves as the stock {@link TimetableComparator}.
 */
public class LexicographicComparator implements SolutionComparator<Lecture, Placement> {
    private final TimetableComparator iFallback;
    private static final double EPS = 1e-9;

    public LexicographicComparator(DataProperties properties) {
        iFallback = new TimetableComparator(properties);
    }

    static double softPenalty(TimetableModel model, Assignment<Lecture, Placement> assignment) {
        double v = 0;
        Criterion<Lecture, Placement> c;
        if ((c = model.getCriterion(TimePreferences.class)) != null) v += c.getValue(assignment);
        if ((c = model.getCriterion(RoomPreferences.class)) != null) v += c.getValue(assignment);
        if ((c = model.getCriterion(DistributionPreferences.class)) != null) v += c.getValue(assignment);
        return v;
    }

    @Override
    public boolean isBetterThanBestSolution(Solution<Lecture, Placement> solution) {
        TimetableModel model = (TimetableModel) solution.getModel();
        RlRuntime rt = RlRuntime.get(model);
        if (rt == null) return iFallback.isBetterThanBestSolution(solution);
        if (solution.getBestInfo() == null) return true;
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        int bestUnassigned = model.getBestUnassignedVariables();
        int unassigned = assignment.nrUnassignedVariables(model);
        if (bestUnassigned >= 0 && unassigned != bestUnassigned) return unassigned < bestUnassigned;
        if (!rt.hasIncumbent()) return true;
        double c = rt.sync(assignment).studentViolationRate();
        if (Math.abs(c - rt.bestC()) > EPS) return c < rt.bestC();
        double o = Math.max(0.0, Math.min(rt.config.oClip, softPenalty(model, assignment) / rt.scales.o));
        return o < rt.bestO() - EPS;
    }
}
