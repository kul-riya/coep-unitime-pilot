package org.unitime.timetable.solver.rl;

import java.util.Collection;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.coursett.sectioning.StudentMove;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.model.Constraint;
import org.cpsolver.ifs.model.ModelListener;
import org.cpsolver.ifs.model.Neighbour;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solution.SolutionListener;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.solver.SolverListener;

/**
 * Per-model runtime shared by {@link RlNeighbourSelection}, {@link LexicographicComparator},
 * {@link RlTerminationCondition} and the headless runner. It owns the {@link ConflictOracle}, tracks
 * which lectures changed since the last oracle sync (model listener), whether students were moved
 * between sections (solver listener), the number of committed neighbourhoods, and the metrics of the
 * incumbent (solution listener on bestSaved).
 *
 * Classes that CPSolver instantiates by reflection (comparator, termination) find the runtime via
 * {@link #get(TimetableModel)}.
 */
public class RlRuntime implements ModelListener<Lecture, Placement>, SolverListener<Lecture, Placement>, SolutionListener<Lecture, Placement> {
    private static final Logger sLog = LogManager.getLogger(RlRuntime.class);
    private static final Map<TimetableModel, RlRuntime> sRegistry = new WeakHashMap<TimetableModel, RlRuntime>();

    public final TimetableModel model;
    public final RlConfig config;
    public final ConflictOracle oracle;
    public final SearchMetrics.Scales scales;

    private final Set<Lecture> iDirty = new HashSet<Lecture>();
    private boolean iSectioningDirty = false;
    private long iCommitted = 0;
    private long iLastChangeIteration = -1;
    private int iMacroStep = 0;
    private Solver<Lecture, Placement> iSolver = null;
    private Solution<Lecture, Placement> iSolution = null;
    private double iStartTime = 0;
    private PolicyClient iExternalPolicy = null;

    /** Policy injected by the environment (Rl.Policy=bridge). */
    public void setExternalPolicy(PolicyClient policy) { iExternalPolicy = policy; }
    public PolicyClient getExternalPolicy() { return iExternalPolicy; }

    // incumbent (best solution under the active comparator)
    private double iBestC = Double.NaN, iBestO = Double.NaN, iBestU = Double.NaN, iBestPotential = Double.NaN;
    private long iBestIteration = -1;
    private int iBestMacroStep = -1;
    private final Map<String, Long> iThresholdIteration = new LinkedHashMap<String, Long>();
    private final Map<String, Integer> iThresholdMacroStep = new LinkedHashMap<String, Integer>();
    private final Map<String, Double> iThresholdTime = new LinkedHashMap<String, Double>();
    private static final double[] THRESHOLDS = {0.40, 0.30, 0.25};
    /** (iteration, time, C) each time the incumbent's violation rate improved */
    private final java.util.List<double[]> iCHistory = new java.util.ArrayList<double[]>();
    private double iLowestC = Double.NaN;

    private RlRuntime(TimetableModel model, RlConfig config) {
        this.model = model;
        this.config = config;
        this.oracle = new ConflictOracle(model);
        this.scales = new SearchMetrics.Scales(config);
    }

    public static synchronized RlRuntime getOrCreate(TimetableModel model, RlConfig config) {
        RlRuntime rt = sRegistry.get(model);
        if (rt == null) {
            rt = new RlRuntime(model, config);
            sRegistry.put(model, rt);
        }
        return rt;
    }

    public static synchronized RlRuntime get(TimetableModel model) {
        return sRegistry.get(model);
    }

    public static synchronized void remove(TimetableModel model) {
        RlRuntime rt = sRegistry.remove(model);
        if (rt != null) rt.detach();
    }

    /** Register listeners on the model, the solver and its current solution. Idempotent per solver. */
    public synchronized void attach(Solver<Lecture, Placement> solver) {
        if (iSolver == solver) return;
        detach();
        iSolver = solver;
        iSolution = solver.currentSolution();
        model.addModelListener(this);
        solver.addSolverListener(this);
        iSolution.addSolutionListener(this);
        iStartTime = System.nanoTime() / 1e9;
        iCommitted = 0;
        iMacroStep = 0;
        iDirty.clear();
        iSectioningDirty = true; // force a full recompute on first sync
        iBestC = iBestO = iBestU = iBestPotential = Double.NaN;
        iBestIteration = -1;
        iBestMacroStep = -1;
        iThresholdIteration.clear();
        iThresholdMacroStep.clear();
        iThresholdTime.clear();
        iCHistory.clear();
        iLowestC = Double.NaN;
    }

    public synchronized void detach() {
        if (iSolver == null) return;
        model.removeModelListener(this);
        iSolver.removeSolverListener(this);
        if (iSolution != null) iSolution.removeSolutionListener(this);
        iSolver = null;
        iSolution = null;
    }

    public Solver<Lecture, Placement> getSolver() { return iSolver; }
    public long getCommitted() { return iCommitted; }
    public int getMacroStep() { return iMacroStep; }
    public void setMacroStep(int step) { iMacroStep = step; }
    public long getLastChangeIteration() { return iLastChangeIteration; }
    public double elapsedSec() { return System.nanoTime() / 1e9 - iStartTime; }

    /** Bring the oracle up to date with the assignment. Cheap when few lectures changed. */
    public synchronized ConflictReport sync(Assignment<Lecture, Placement> assignment) {
        ConflictReport r = oracle.update(assignment, iDirty, iSectioningDirty);
        iDirty.clear();
        iSectioningDirty = false;
        return r;
    }

    /** Lectures changed since the last sync (read-only view for churn features). */
    public synchronized int pendingDirtyCount() { return iDirty.size(); }

    public synchronized void markAllDirty() { iSectioningDirty = true; }

    // ---- ModelListener ----
    @Override public void variableAdded(Lecture variable) {}
    @Override public void variableRemoved(Lecture variable) {}
    @Override public void constraintAdded(Constraint<Lecture, Placement> constraint) {}
    @Override public void constraintRemoved(Constraint<Lecture, Placement> constraint) {}
    @Override public void beforeAssigned(Assignment<Lecture, Placement> assignment, long iteration, Placement value) {}
    @Override public void beforeUnassigned(Assignment<Lecture, Placement> assignment, long iteration, Placement value) {}

    @Override
    public synchronized void afterAssigned(Assignment<Lecture, Placement> assignment, long iteration, Placement value) {
        iDirty.add(value.variable());
        iLastChangeIteration = iteration;
    }

    @Override
    public synchronized void afterUnassigned(Assignment<Lecture, Placement> assignment, long iteration, Placement value) {
        iDirty.add(value.variable());
        iLastChangeIteration = iteration;
    }

    @Override public boolean init(Solver<Lecture, Placement> solver) { return true; }

    // ---- SolverListener ----
    @Override public boolean variableSelected(Assignment<Lecture, Placement> assignment, long iteration, Lecture variable) { return true; }
    @Override public boolean valueSelected(Assignment<Lecture, Placement> assignment, long iteration, Lecture variable, Placement value) { return true; }

    @Override
    public synchronized boolean neighbourSelected(Assignment<Lecture, Placement> assignment, long iteration, Neighbour<Lecture, Placement> neighbour) {
        if (neighbour == null || neighbour instanceof Operators.NoOpNeighbour) return true;
        iCommitted++; // one committed neighbourhood (the solver assigns it right after this call)
        if (neighbour instanceof StudentMove) {
            iSectioningDirty = true;
            iLastChangeIteration = iteration;
        }
        return true;
    }

    @Override public void neighbourFailed(Assignment<Lecture, Placement> assignment, long iteration, Neighbour<Lecture, Placement> neighbour) {}

    // ---- SolutionListener ----
    @Override public void solutionUpdated(Solution<Lecture, Placement> solution) {}
    @Override public void getInfo(Solution<Lecture, Placement> solution, Map<String, String> info) {}
    @Override public void getInfo(Solution<Lecture, Placement> solution, Map<String, String> info, Collection<Lecture> variables) {}
    @Override public void bestCleared(Solution<Lecture, Placement> solution) {}
    @Override public void bestRestored(Solution<Lecture, Placement> solution) { markAllDirty(); }

    /** The current assignment has just become the incumbent: record its cheap metrics. */
    @Override
    public synchronized void bestSaved(Solution<Lecture, Placement> solution) {
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        ConflictReport r = sync(assignment);
        SearchMetrics m = SearchMetrics.compute(model, assignment, r, config, scales, false, solution.getIteration(), solution.getTime());
        iBestC = m.studentViolationRate();
        iBestO = m.softPenaltyNorm;
        iBestU = m.unassignedFraction;
        iBestPotential = m.potential;
        iBestIteration = solution.getIteration();
        iBestMacroStep = iMacroStep;
        if (Double.isNaN(iLowestC) || iBestC < iLowestC - 1e-12) {
            iLowestC = iBestC;
            iCHistory.add(new double[] {solution.getIteration(), solution.getTime(), iBestC});
        }
        for (double t: THRESHOLDS) {
            String key = String.format("%.2f", t);
            if (iBestC <= t && !iThresholdIteration.containsKey(key)) {
                iThresholdIteration.put(key, solution.getIteration());
                iThresholdMacroStep.put(key, iMacroStep);
                iThresholdTime.put(key, solution.getTime());
            }
        }
    }

    public synchronized boolean hasIncumbent() { return !Double.isNaN(iBestC); }
    public synchronized double bestC() { return iBestC; }
    public synchronized double bestO() { return iBestO; }
    public synchronized double bestU() { return iBestU; }
    public synchronized double bestPotential() { return iBestPotential; }
    public synchronized long bestIteration() { return iBestIteration; }
    public synchronized int bestMacroStep() { return iBestMacroStep; }

    /** Improvement history of the incumbent's C: list of {iteration, time_sec, C}. */
    public synchronized java.util.List<Map<String, Object>> cHistory() {
        java.util.List<Map<String, Object>> list = new java.util.ArrayList<Map<String, Object>>();
        for (double[] e: iCHistory) {
            Map<String, Object> m = new LinkedHashMap<String, Object>();
            m.put("iteration", (long) e[0]);
            m.put("time_sec", e[1]);
            m.put("C", e[2]);
            list.add(m);
        }
        return list;
    }

    public synchronized Map<String, Object> thresholdReport() {
        Map<String, Object> map = new LinkedHashMap<String, Object>();
        for (double t: THRESHOLDS) {
            String key = String.format("%.2f", t);
            Map<String, Object> e = new LinkedHashMap<String, Object>();
            e.put("iteration", iThresholdIteration.get(key));
            e.put("macro_step", iThresholdMacroStep.get(key));
            e.put("time_sec", iThresholdTime.get(key));
            map.put("first_reach_" + key, e);
        }
        return map;
    }

    /** Debug helper. */
    public void logState(String prefix) {
        sLog.info(prefix + " committed=" + iCommitted + " macroStep=" + iMacroStep + " bestC=" + iBestC + " oracle(full=" + oracle.getFullRecomputes() + ", inc=" + oracle.getIncrementalUpdates() + ")");
    }
}
