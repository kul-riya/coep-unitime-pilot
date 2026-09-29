package org.unitime.timetable.solver.rl;

import java.util.HashSet;
import java.util.Set;

import org.cpsolver.ifs.util.DataProperties;

/**
 * All Rl.* solver properties in one place. Every value has a default so the class works from a
 * stock UniTime configuration with only {@code General.SearchAlgorithm=RL} added.
 */
public class RlConfig {
    public final DataProperties properties;

    /** macro-action length: solver iterations per policy decision */
    public final int k;
    /** truncate an episode after this many macro-steps (-1 = never) */
    public final int maxMacroSteps;
    /** stop after this many committed neighbourhoods (-1 = never); the secondary budget of the bake-off */
    public final long maxCommitted;
    /** onnx | linucb | random | fixed | grpc | bridge | none */
    public final String policy;
    /** act | shadow. Shadow executes the default selector and only logs the policy's choice. */
    public final String mode;
    public final String onnxPath;
    public final boolean onnxStochastic;
    public final double onnxTimeoutMs;
    public final int onnxMaxSlowCalls;
    public final String grpcTarget;
    public final long grpcDeadlineMs;
    public final int fixedAction;
    public final double linUcbAlpha, linUcbLambda, linUcbRewardScale;
    public final double wC, wU, wH, wO, stepPenalty, oClip;
    public final int driftCheckInterval;
    public final int maxProposalsPerIteration;
    public final Set<Integer> disabledOperators = new HashSet<Integer>();
    public final String trajectoryLog;
    public final boolean allowUnassignments;
    public final long seed;

    public RlConfig(DataProperties p) {
        properties = p;
        k = p.getPropertyInt("Rl.K", 50);
        maxMacroSteps = p.getPropertyInt("Rl.MaxMacroSteps", -1);
        maxCommitted = p.getPropertyLong("Rl.MaxCommitted", -1L);
        policy = p.getProperty("Rl.Policy", "onnx");
        mode = p.getProperty("Rl.Mode", "act");
        onnxPath = p.getProperty("Rl.Onnx.Path", null);
        onnxStochastic = p.getPropertyBoolean("Rl.Onnx.Stochastic", false);
        onnxTimeoutMs = p.getPropertyDouble("Rl.Onnx.TimeoutMs", 1.0);
        onnxMaxSlowCalls = p.getPropertyInt("Rl.Onnx.MaxSlowCalls", 1000);
        grpcTarget = p.getProperty("Rl.Grpc.Target", "localhost:50052");
        grpcDeadlineMs = p.getPropertyLong("Rl.Grpc.DeadlineMs", 1000L);
        fixedAction = p.getPropertyInt("Rl.Fixed.Action", 0);
        linUcbAlpha = p.getPropertyDouble("Rl.LinUcb.Alpha", 0.5);
        linUcbLambda = p.getPropertyDouble("Rl.LinUcb.Lambda", 1.0);
        linUcbRewardScale = p.getPropertyDouble("Rl.LinUcb.RewardScale", 100.0);
        wC = p.getPropertyDouble("Rl.Potential.C", 1.00);
        wU = p.getPropertyDouble("Rl.Potential.U", 0.50);
        wH = p.getPropertyDouble("Rl.Potential.H", 5.00);
        wO = p.getPropertyDouble("Rl.Potential.O", 0.05);
        stepPenalty = p.getPropertyDouble("Rl.StepPenalty", 1e-4);
        oClip = p.getPropertyDouble("Rl.OClip", 3.0);
        driftCheckInterval = p.getPropertyInt("Rl.DriftCheckInterval", 20);
        maxProposalsPerIteration = p.getPropertyInt("Rl.MaxProposalsPerIteration", 200);
        String disabled = p.getProperty("Rl.DisabledOperators", "");
        for (String s: disabled.split("[,;\\s]+"))
            if (!s.isEmpty()) disabledOperators.add(Integer.valueOf(s.trim()));
        trajectoryLog = p.getProperty("Rl.TrajectoryLog", null);
        allowUnassignments = p.getPropertyBoolean("Suggestion.AllowUnassignments", false);
        seed = p.getPropertyLong("General.Seed", -1L);
    }

    /** Scale for a normalised objective term: Rl.Scale.&lt;name&gt;, or the supplied fallback. */
    public double scale(String name, double fallback) {
        double s = properties.getPropertyDouble("Rl.Scale." + name, fallback);
        return s > 0 ? s : 1.0;
    }

    public boolean hasScale(String name) {
        return properties.getProperty("Rl.Scale." + name) != null;
    }

    public boolean isShadow() { return "shadow".equalsIgnoreCase(mode); }
}
