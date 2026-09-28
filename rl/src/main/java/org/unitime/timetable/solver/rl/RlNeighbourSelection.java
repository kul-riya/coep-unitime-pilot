package org.unitime.timetable.solver.rl;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.coursett.heuristics.FixCompleteSolutionNeighbourSelection;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.algorithms.GreatDeluge;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.heuristics.NeighbourSelection;
import org.cpsolver.ifs.heuristics.StandardNeighbourSelection;
import org.cpsolver.ifs.model.Neighbour;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.util.DataProperties;

/**
 * Learned operator selection for the course timetabling search.
 *
 * <p>Set with {@code Neighbour.Class=org.unitime.timetable.solver.rl.RlNeighbourSelection}
 * ({@code General.SearchAlgorithm=RL} in UniTime). Every {@link #selectNeighbour(Solution)} call is
 * one solver iteration. At every K-th call (a macro-step boundary) the state is encoded, the reward
 * of the finished macro-step is computed on the incumbent, and the policy picks one of the eight
 * operators in {@link Operators}. Inside the macro-step the chosen operator proposes neighbours and
 * CPSolver's own Great Deluge acceptance commits or rejects them. The wrapper never writes an
 * assignment itself, so hard constraints are enforced by the delegates exactly as in a stock solve.
 *
 * <p>Modes: {@code Rl.Mode=act} (policy drives the search) or {@code Rl.Mode=shadow} (the default
 * selector drives the search; the policy is only asked and logged, producing behaviour-cloning data
 * and a disagreement rate). If the policy cannot be created or throws, the run flips to
 * {@link FixCompleteSolutionNeighbourSelection} for the rest of the solve and logs the cause.
 */
public class RlNeighbourSelection implements NeighbourSelection<Lecture, Placement> {
    private static final Logger sLog = LogManager.getLogger(RlNeighbourSelection.class);

    private final DataProperties iProperties;
    private final RlConfig iConfig;
    private RlRuntime iRuntime;
    private Solver<Lecture, Placement> iSolver;
    private TimetableModel iModel;
    private List<NeighbourSelection<Lecture, Placement>> iOperators;
    private RlDeluge iDeluge;
    private NeighbourSelection<Lecture, Placement> iConstruction;
    private NeighbourSelection<Lecture, Placement> iDefault;
    private NeighbourSelection<Lecture, Placement> iFallback = null;
    private String iFallbackReason = null;
    private PolicyClient iPolicy = null;
    private TrajectoryLogger iLog = null;
    private final boolean iShadow;

    // macro-step state
    private int iAction = -1;
    private int iIterInStep = 0;
    private int iMacroStep = 0;
    private boolean[] iMask = new boolean[Operators.COUNT];
    private int iProposals = 0, iNulls = 0, iAccepted = 0, iIdle = 0, iProposalsThisCall = 0;
    private int iSubDecisions = 0;
    private final int[] iLabelHist = new int[Operators.COUNT];
    private int iPolicyAction = -1;
    private float[] iPrevObs = null;
    private boolean[] iPrevMask = null;
    private double iPrevIncumbentPotential = Double.NaN;
    private double iPrevC = Double.NaN, iBestC = Double.NaN;
    private long iCommittedAtBoundary = 0;
    private boolean iTruncated = false;
    private boolean iFinished = false;
    private SearchMetrics iLastMetrics = null;
    private int iDisagreements = 0, iComparableSteps = 0;
    private long iBoundaryNs = 0;

    public RlNeighbourSelection(DataProperties properties) throws Exception {
        iProperties = properties;
        iConfig = new RlConfig(properties);
        iShadow = iConfig.isShadow();
        iDefault = new FixCompleteSolutionNeighbourSelection(properties);
        iConstruction = new StandardNeighbourSelection<Lecture, Placement>(properties);
    }

    public RlConfig getConfig() { return iConfig; }
    public RlRuntime getRuntime() { return iRuntime; }
    public PolicyClient getPolicy() { return iPolicy; }
    public boolean isFallback() { return iFallback != null; }
    public String getFallbackReason() { return iFallbackReason; }
    public int getMacroStep() { return iMacroStep; }
    public boolean isTruncated() { return iTruncated; }
    public SearchMetrics getLastMetrics() { return iLastMetrics; }
    public double getDisagreementRate() { return iComparableSteps == 0 ? Double.NaN : (double) iDisagreements / iComparableSteps; }
    public double meanBoundaryMs() { return iMacroStep == 0 ? 0 : iBoundaryNs / 1e6 / iMacroStep; }

    @Override
    public void init(Solver<Lecture, Placement> solver) {
        iSolver = solver;
        iModel = (TimetableModel) solver.currentSolution().getModel();
        iRuntime = RlRuntime.getOrCreate(iModel, iConfig);
        iRuntime.attach(solver);
        iDefault.init(solver);
        iConstruction.init(solver);
        try {
            iOperators = Operators.create(iProperties, iRuntime);
            for (NeighbourSelection<Lecture, Placement> op: iOperators) op.init(solver);
            iDeluge = new RlDeluge(iProperties);
            iDeluge.init(solver);
        } catch (Exception e) {
            fallback("cannot create operators: " + e.getMessage(), e);
            return;
        }
        if (iConfig.trajectoryLog != null) iLog = new TrajectoryLogger(iConfig.trajectoryLog);
        try {
            iPolicy = createPolicy();
        } catch (Exception e) {
            fallback("cannot create policy '" + iConfig.policy + "': " + e.getMessage(), e);
            return;
        }
        if (iPolicy == null && !iShadow) {
            fallback("no policy configured (Rl.Policy=" + iConfig.policy + ") and Rl.Mode is not shadow", null);
            return;
        }
        for (int i = 0; i < Operators.COUNT; i++) iMask[i] = true;
        sLog.info("RL neighbour selection: mode=" + iConfig.mode + " policy=" + (iPolicy == null ? "none" : iPolicy.name())
                + " K=" + iConfig.k + " maxMacroSteps=" + iConfig.maxMacroSteps);
    }

    private PolicyClient createPolicy() throws Exception {
        String p = iConfig.policy.toLowerCase();
        switch (p) {
            case "onnx": return new OnnxPolicy(iConfig);
            case "grpc": return new GrpcPolicy(iConfig);
            case "linucb": return new LinUcbPolicy(iConfig);
            case "random": return new SimplePolicies.RandomPolicy();
            case "roundrobin": return new SimplePolicies.RoundRobinPolicy();
            case "fixed": return new SimplePolicies.FixedPolicy(iConfig.fixedAction);
            case "bridge": {
                PolicyClient external = iRuntime.getExternalPolicy();
                if (external == null) throw new IllegalStateException("Rl.Policy=bridge but no BridgePolicy registered on the runtime");
                return external;
            }
            case "none": return null;
            default: throw new IllegalArgumentException("unknown Rl.Policy " + iConfig.policy);
        }
    }

    private void fallback(String reason, Throwable t) {
        if (iFallback != null) return;
        iFallbackReason = reason;
        iFallback = iDefault;
        if (t != null) sLog.error("RL selector falling back to " + iDefault.getClass().getSimpleName() + ": " + reason, t);
        else sLog.warn("RL selector falling back to " + iDefault.getClass().getSimpleName() + ": " + reason);
        if (iPolicy != null) { try { iPolicy.close(); } catch (Exception e) { /* ignore */ } iPolicy = null; }
    }

    @Override
    public Neighbour<Lecture, Placement> selectNeighbour(Solution<Lecture, Placement> solution) {
        if (iFallback != null) return iFallback.selectNeighbour(solution);
        if (iTruncated) return null;
        try {
            Assignment<Lecture, Placement> assignment = solution.getAssignment();
            if (iModel.nrUnassignedVariables(assignment) > 0) {
                if (!iConfig.allowUnassignments && iModel.getBestUnassignedVariables() == 0) {
                    solution.restoreBest();
                } else {
                    Neighbour<Lecture, Placement> n = iConstruction.selectNeighbour(solution);
                    if (n != null) return n;
                }
            }
            if (iIterInStep == 0) {
                if (!beginMacroStep(solution)) return null;
            }
            iIterInStep++;
            if (iIterInStep >= iConfig.k) iIterInStep = 0;
            iProposalsThisCall = 0;
            Neighbour<Lecture, Placement> n;
            if (iShadow) {
                n = iDefault.selectNeighbour(solution);
                int label = OperatorLabeler.label(n, assignment);
                if (label >= 0) iLabelHist[label]++;
            } else {
                n = iDeluge.selectNeighbour(solution);
            }
            if (n == null || n instanceof Operators.NoOpNeighbour) iIdle++; else iAccepted++;
            return n;
        } catch (PolicyClient.EpisodeAborted e) {
            iTruncated = true;
            iSolver.stopSolver(false); // never join from the solver thread itself
            return null;
        } catch (RuntimeException e) {
            fallback("exception in RL selection: " + e.getMessage(), e);
            return iFallback.selectNeighbour(solution);
        }
    }

    /**
     * Macro-step boundary: finish the previous step (reward on the incumbent, log), encode the state,
     * ask the policy. @return false when the episode is truncated (the solver is asked to stop).
     */
    private boolean beginMacroStep(Solution<Lecture, Placement> solution) throws PolicyClient.EpisodeAborted {
        long t0 = System.nanoTime();
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        ConflictReport report = iRuntime.sync(assignment);
        if (iConfig.driftCheckInterval > 0 && iMacroStep > 0 && iMacroStep % iConfig.driftCheckInterval == 0) {
            double drift = iRuntime.oracle.driftCheck(assignment);
            if (drift > 1e-9) sLog.warn("conflict oracle drift " + drift + " at macro-step " + iMacroStep + " (full recompute applied)");
            report = iRuntime.oracle.last(assignment);
        }
        SearchMetrics m = SearchMetrics.compute(iModel, assignment, report, iConfig, iRuntime.scales, true, solution.getIteration(), solution.getTime());
        iLastMetrics = m;
        double incumbentPotential = incumbentPotential(m);
        double reward = (iMacroStep == 0 || Double.isNaN(iPrevIncumbentPotential)) ? 0.0 : (incumbentPotential - iPrevIncumbentPotential) - iConfig.stepPenalty;

        StateEncoder.Dynamics d = new StateEncoder.Dynamics();
        d.bestC = iBestC;
        d.previousC = iPrevC;
        d.progress = progress(solution);
        d.acceptanceRate = iProposals == 0 ? 0.0 : (double) iAccepted / iProposals;
        d.idleFraction = iConfig.k == 0 ? 0.0 : (double) iIdle / iConfig.k;
        d.nullFraction = iProposals == 0 ? 0.0 : (double) iNulls / iProposals;
        d.previousAction = iAction;
        long committed = iRuntime.getCommitted();
        d.churn = iModel.variables().isEmpty() ? 0.0 : (double) (committed - iCommittedAtBoundary) / iModel.variables().size();
        float[] obs = StateEncoder.encode(m, iRuntime.scales, d, iConfig);
        boolean[] mask = baseMask(report, assignment);

        if (iMacroStep > 0) logStep(obs, reward, m, solution);

        iRuntime.setMacroStep(iMacroStep);
        if (iConfig.maxMacroSteps >= 0 && iMacroStep >= iConfig.maxMacroSteps) {
            iTruncated = true;
            iSolver.stopSolver(false); // sets the stop flag; joining here would deadlock the solver thread
            return false;
        }

        PolicyClient.StepContext ctx = new PolicyClient.StepContext();
        ctx.obs = obs; ctx.mask = mask; ctx.reward = reward; ctx.metrics = m; ctx.macroStep = iMacroStep;
        ctx.previousAction = iAction; ctx.firstStep = (iMacroStep == 0);
        int action = -1;
        if (iPolicy != null) {
            try {
                action = iPolicy.act(ctx);
            } catch (PolicyClient.EpisodeAborted e) {
                throw e;
            } catch (Exception e) {
                fallback("policy failure: " + e.getMessage(), e);
                return false;
            }
        }
        if (!iShadow && (action < 0 || action >= Operators.COUNT || !mask[action])) action = PolicyClient.firstAllowed(mask);
        iPolicyAction = action; // the boundary decision; iAction may move on within the step after null returns
        iAction = action;
        iMask = mask;
        iPrevObs = obs;
        iPrevMask = mask.clone();
        iPrevIncumbentPotential = incumbentPotential;
        double c = m.studentViolationRate();
        iPrevC = c;
        iBestC = Double.isNaN(iBestC) ? c : Math.min(iBestC, c);
        iProposals = iNulls = iAccepted = iIdle = iSubDecisions = 0;
        java.util.Arrays.fill(iLabelHist, 0);
        iCommittedAtBoundary = committed;
        iMacroStep++;
        iBoundaryNs += System.nanoTime() - t0;
        return true;
    }

    private double incumbentPotential(SearchMetrics current) {
        if (!iRuntime.hasIncumbent()) return current.potential;
        int h = 0;
        // when the current assignment is the incumbent, its hard-violation scan is available
        if (iRuntime.bestIteration() >= iRuntime.getLastChangeIteration()) h = current.hardViolations;
        return SearchMetrics.potential(iConfig, iRuntime.bestC(), iRuntime.bestU(), h, iRuntime.bestO());
    }

    private double progress(Solution<Lecture, Placement> solution) {
        double p = 0;
        double timeout = iProperties.getPropertyDouble("Termination.TimeOut", -1.0);
        if (timeout > 0) p = Math.max(p, solution.getTime() / timeout);
        long maxIters = iProperties.getPropertyLong("Termination.MaxIters", -1L);
        if (maxIters > 0) p = Math.max(p, (double) solution.getIteration() / maxIters);
        if (iConfig.maxMacroSteps > 0) p = Math.max(p, (double) iMacroStep / iConfig.maxMacroSteps);
        if (iConfig.maxCommitted > 0) p = Math.max(p, (double) iRuntime.getCommitted() / iConfig.maxCommitted);
        return Math.min(1.0, p);
    }

    /** True when at least one class has an alternative section, so a student swap can exist. */
    private Boolean iHasSectionAlternatives = null;

    private boolean hasSectionAlternatives() {
        if (iHasSectionAlternatives == null) {
            boolean any = false;
            for (Lecture l: iModel.variables()) {
                if (l.sameSubpartLectures() != null && l.sameSubpartLectures().size() > 1) { any = true; break; }
                if (l.getConfiguration() != null && l.getConfiguration().getAltConfigurations() != null && !l.getConfiguration().getAltConfigurations().isEmpty()) { any = true; break; }
            }
            iHasSectionAlternatives = any;
        }
        return iHasSectionAlternatives;
    }

    private boolean[] baseMask(ConflictReport report, Assignment<Lecture, Placement> assignment) {
        boolean[] mask = new boolean[Operators.COUNT];
        boolean students = !iModel.getAllStudents().isEmpty() && iSolver.hasSingleSolution() && hasSectionAlternatives();
        for (int i = 0; i < Operators.COUNT; i++) mask[i] = !iConfig.disabledOperators.contains(i);
        if (!students) { mask[Operators.STUDENT_SWAP] = false; mask[Operators.BIASED_STUDENT_SWAP] = false; }
        if (report.conflicted.isEmpty()) mask[Operators.BIASED_STUDENT_SWAP] = false;
        if (report.classScores.isEmpty()) mask[Operators.BIASED_TIME_CHANGE] = false;
        // the stock Suggestion neighbourhood only repairs unassigned classes
        if (iModel.nrUnassignedVariables(assignment) == 0) mask[Operators.SUGGESTION] = false;
        boolean any = false;
        for (boolean b: mask) any |= b;
        if (!any) mask[Operators.TIME_CHANGE] = true;
        return mask;
    }

    private void logStep(float[] nextObs, double reward, SearchMetrics m, Solution<Lecture, Placement> solution) {
        int label = -1, labelCount = 0, labelTotal = 0;
        for (int i = 0; i < Operators.COUNT; i++) {
            labelTotal += iLabelHist[i];
            if (iLabelHist[i] > labelCount) { labelCount = iLabelHist[i]; label = i; }
        }
        if (iShadow && label >= 0 && iPolicyAction >= 0) {
            iComparableSteps++;
            if (label != iPolicyAction) iDisagreements++;
        }
        if (iLog == null) return;
        Map<String, Object> rec = new LinkedHashMap<String, Object>();
        rec.put("macro_step", iMacroStep - 1);
        rec.put("iteration", solution.getIteration());
        rec.put("time_sec", solution.getTime());
        rec.put("action", iShadow ? label : iPolicyAction);   // what was executed at the boundary (shadow: the default selector's operator)
        rec.put("policy_action", iPolicyAction);              // the policy's boundary decision
        rec.put("final_action", iAction);                     // operator in effect at the end of the step (after null re-queries)
        rec.put("label", label);
        rec.put("label_hist", iLabelHist.clone());
        rec.put("label_total", labelTotal);
        rec.put("reward", reward);
        rec.put("obs", iPrevObs);
        rec.put("mask", iPrevMask);
        rec.put("next_obs", nextObs);
        rec.put("proposals", iProposals);
        rec.put("nulls", iNulls);
        rec.put("accepted", iAccepted);
        rec.put("idle", iIdle);
        rec.put("sub_decisions", iSubDecisions);
        rec.put("committed", iRuntime.getCommitted());
        rec.put("incumbent_c", iRuntime.bestC());
        rec.put("incumbent_potential", iPrevIncumbentPotential);
        rec.put("metrics", m.toMap());
        iLog.log(rec);
    }

    /**
     * Terminal bookkeeping once the solver thread has stopped: metrics of the final incumbent, the
     * terminal reward, the last trajectory record. Safe to call more than once.
     */
    public synchronized SearchMetrics finish(Solution<Lecture, Placement> solution) {
        if (iFinished) return iLastMetrics;
        iFinished = true;
        if (iRuntime == null) return null;
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        ConflictReport report = iRuntime.oracle.evaluate(assignment);
        SearchMetrics m = SearchMetrics.compute(iModel, assignment, report, iConfig, iRuntime.scales, true, solution.getIteration(), solution.getTime());
        iLastMetrics = m;
        double incumbentPotential = incumbentPotential(m);
        double reward = Double.isNaN(iPrevIncumbentPotential) ? 0.0 : (incumbentPotential - iPrevIncumbentPotential) - iConfig.stepPenalty;
        if (iMacroStep > 0 && iFallback == null) {
            StateEncoder.Dynamics d = new StateEncoder.Dynamics();
            d.bestC = iBestC; d.previousC = iPrevC; d.progress = 1.0; d.previousAction = iAction;
            float[] obs = StateEncoder.encode(m, iRuntime.scales, d, iConfig);
            logStep(obs, reward, m, solution);
            if (iPolicy != null) {
                PolicyClient.StepContext ctx = new PolicyClient.StepContext();
                ctx.obs = obs; ctx.mask = iMask; ctx.reward = reward; ctx.metrics = m; ctx.macroStep = iMacroStep;
                try { iPolicy.finish(ctx); } catch (Exception e) { sLog.warn("policy finish: " + e.getMessage()); }
            }
        }
        m.potential = incumbentPotential;
        return m;
    }

    /** Terminal reward of the last (possibly partial) macro-step, for the environment. */
    public double terminalReward(SearchMetrics terminal) {
        if (Double.isNaN(iPrevIncumbentPotential)) return 0.0;
        return terminal.potential - iPrevIncumbentPotential - iConfig.stepPenalty;
    }

    /** Release listeners, policy and log. Call after the solver thread has ended. */
    public void dispose() {
        if (iPolicy != null && !(iPolicy instanceof BridgePolicy)) { try { iPolicy.close(); } catch (Exception e) { /* ignore */ } }
        if (iLog != null) iLog.close();
        if (iDeluge != null && iSolver != null) iSolver.currentSolution().removeSolutionListener(iDeluge);
        if (iRuntime != null) iRuntime.detach();
    }

    public Map<String, Object> summary() {
        Map<String, Object> s = new LinkedHashMap<String, Object>();
        s.put("mode", iConfig.mode);
        s.put("policy", iPolicy == null ? iConfig.policy : iPolicy.name());
        s.put("k", iConfig.k);
        s.put("macro_steps", iMacroStep);
        s.put("fallback", iFallback != null);
        s.put("fallback_reason", iFallbackReason);
        s.put("truncated", iTruncated);
        s.put("disagreement_rate", getDisagreementRate());
        s.put("mean_boundary_ms", meanBoundaryMs());
        if (iPolicy instanceof OnnxPolicy) s.put("mean_forward_ms", ((OnnxPolicy) iPolicy).meanForwardMs());
        if (iPolicy instanceof LinUcbPolicy) s.put("linucb_pulls", ((LinUcbPolicy) iPolicy).pulls());
        return s;
    }

    /**
     * Great Deluge whose move generator is the operator chosen by the policy. A delegate returning
     * null masks that operator for the rest of the macro-step and the policy is re-asked with the
     * updated mask (same state, no reward). When every operator is masked, or a proposal cap is hit,
     * a no-op neighbour is returned so the acceptance loop terminates.
     */
    private class RlDeluge extends GreatDeluge<Lecture, Placement> {
        RlDeluge(DataProperties properties) {
            super(trimmed(properties));
        }

        @Override
        public Neighbour<Lecture, Placement> generateMove(Solution<Lecture, Placement> solution) {
            iProposals++;
            if (++iProposalsThisCall > iConfig.maxProposalsPerIteration) return Operators.NoOpNeighbour.INSTANCE;
            if (iAction < 0 || !iMask[iAction]) {
                if (!requery(solution)) return Operators.NoOpNeighbour.INSTANCE;
            }
            Neighbour<Lecture, Placement> n = iOperators.get(iAction).selectNeighbour(solution);
            if (n == null) {
                iNulls++;
                iMask[iAction] = false;
                if (!requery(solution)) return Operators.NoOpNeighbour.INSTANCE;
                return null;
            }
            return n;
        }

        private boolean requery(Solution<Lecture, Placement> solution) {
            boolean any = false;
            for (boolean b: iMask) any |= b;
            if (!any) return false;
            iSubDecisions++;
            PolicyClient.StepContext ctx = new PolicyClient.StepContext();
            ctx.obs = iPrevObs; ctx.mask = iMask; ctx.reward = 0.0; ctx.metrics = iLastMetrics;
            ctx.macroStep = iMacroStep - 1; ctx.previousAction = iAction; ctx.firstStep = false;
            int a;
            try {
                a = (iPolicy == null || iPolicy instanceof BridgePolicy) ? PolicyClient.firstAllowed(iMask) : iPolicy.act(ctx);
            } catch (PolicyClient.EpisodeAborted e) {
                throw e;
            } catch (Exception e) {
                fallback("policy failure on re-query: " + e.getMessage(), e);
                return false;
            }
            if (a < 0 || a >= Operators.COUNT || !iMask[a]) a = PolicyClient.firstAllowed(iMask);
            iAction = a;
            return true;
        }
    }

    /** The mixture neighbours of the stock Great Deluge are actions here; do not build them twice. */
    private static DataProperties trimmed(DataProperties properties) {
        DataProperties p = new DataProperties(properties);
        p.setProperty("GreatDeluge.Neighbours", "org.cpsolver.ifs.algorithms.neighbourhoods.RandomMove");
        p.setProperty("GreatDeluge.AdditionalNeighbours", "");
        return p;
    }
}
