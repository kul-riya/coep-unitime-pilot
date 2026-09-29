package org.unitime.timetable.solver.rl;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.termination.TerminationCondition;
import org.cpsolver.ifs.util.DataProperties;

/**
 * Termination.TimeOut (wall-clock, the primary budget), Termination.MaxIters, Rl.MaxCommitted
 * (accepted neighbourhoods, the secondary budget) and Rl.MaxMacroSteps (episode truncation).
 * Set with {@code Termination.Class=org.unitime.timetable.solver.rl.RlTerminationCondition}.
 */
public class RlTerminationCondition implements TerminationCondition<Lecture, Placement> {
    private final long iMaxIter;
    private final double iTimeOut;
    private final long iMaxCommitted;
    private final int iMaxMacroSteps;
    private final boolean iStopWhenComplete;

    public RlTerminationCondition(DataProperties properties) {
        iMaxIter = properties.getPropertyLong("Termination.MaxIters", -1L);
        iTimeOut = properties.getPropertyDouble("Termination.TimeOut", -1.0);
        iMaxCommitted = properties.getPropertyLong("Rl.MaxCommitted", -1L);
        iMaxMacroSteps = properties.getPropertyInt("Rl.MaxMacroSteps", -1);
        iStopWhenComplete = properties.getPropertyBoolean("Termination.StopWhenComplete", false);
    }

    @Override
    public boolean canContinue(Solution<Lecture, Placement> solution) {
        if (iMaxIter >= 0 && solution.getIteration() >= iMaxIter) return false;
        if (iTimeOut >= 0 && solution.getTime() > iTimeOut) return false;
        if (iStopWhenComplete && solution.getModel().nrUnassignedVariables(solution.getAssignment()) == 0) return false;
        RlRuntime rt = RlRuntime.get((TimetableModel) solution.getModel());
        if (rt != null) {
            if (iMaxCommitted >= 0 && rt.getCommitted() >= iMaxCommitted) return false;
            if (iMaxMacroSteps >= 0 && rt.getMacroStep() >= iMaxMacroSteps) return false;
        }
        return true;
    }
}
