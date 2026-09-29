package org.unitime.timetable.solver.rl;

import org.cpsolver.ifs.util.ToolBox;

/**
 * Arm L of the bake-off: disjoint LinUCB over the eight operators with the 48-dim state as context.
 * Answers "is a contextual bandit enough, or is PPO needed?". The reward of a step is the potential
 * difference of the incumbent (same as PPO), scaled by Rl.LinUcb.RewardScale.
 */
public class LinUcbPolicy implements PolicyClient {
    private final int d = StateEncoder.DIM;
    private final double iAlpha, iRewardScale;
    private final double[][][] iAinv = new double[Operators.COUNT][][];
    private final double[][] iB = new double[Operators.COUNT][];
    private float[] iLastObs = null;
    private int iLastAction = -1;
    private final long[] iPulls = new long[Operators.COUNT];

    public LinUcbPolicy(RlConfig cfg) {
        iAlpha = cfg.linUcbAlpha;
        iRewardScale = cfg.linUcbRewardScale;
        for (int a = 0; a < Operators.COUNT; a++) {
            iAinv[a] = new double[d][d];
            for (int i = 0; i < d; i++) iAinv[a][i][i] = 1.0 / cfg.linUcbLambda;
            iB[a] = new double[d];
        }
    }

    private void update(int a, float[] x, double r) {
        double[][] Ainv = iAinv[a];
        double[] Ax = new double[d];
        double xAx = 0;
        for (int i = 0; i < d; i++) {
            double s = 0;
            for (int j = 0; j < d; j++) s += Ainv[i][j] * x[j];
            Ax[i] = s;
            xAx += x[i] * s;
        }
        double denom = 1.0 + xAx;
        for (int i = 0; i < d; i++)
            for (int j = 0; j < d; j++)
                Ainv[i][j] -= Ax[i] * Ax[j] / denom;
        for (int i = 0; i < d; i++) iB[a][i] += r * x[i];
        iPulls[a]++;
    }

    private double score(int a, float[] x) {
        double[][] Ainv = iAinv[a];
        double[] theta = new double[d];
        double[] Ax = new double[d];
        double xAx = 0;
        for (int i = 0; i < d; i++) {
            double t = 0, s = 0;
            for (int j = 0; j < d; j++) { t += Ainv[i][j] * iB[a][j]; s += Ainv[i][j] * x[j]; }
            theta[i] = t; Ax[i] = s;
        }
        double mean = 0;
        for (int i = 0; i < d; i++) { mean += theta[i] * x[i]; xAx += x[i] * Ax[i]; }
        return mean + iAlpha * Math.sqrt(Math.max(0, xAx));
    }

    @Override
    public int act(StepContext ctx) {
        if (iLastObs != null && iLastAction >= 0 && !ctx.firstStep)
            update(iLastAction, iLastObs, ctx.reward * iRewardScale);
        int best = -1;
        double bestScore = Double.NEGATIVE_INFINITY;
        int start = ToolBox.random(Operators.COUNT); // random tie-break order
        for (int k = 0; k < Operators.COUNT; k++) {
            int a = (start + k) % Operators.COUNT;
            if (!ctx.mask[a]) continue;
            double s = score(a, ctx.obs);
            if (s > bestScore) { bestScore = s; best = a; }
        }
        if (best < 0) best = PolicyClient.firstAllowed(ctx.mask);
        iLastObs = ctx.obs.clone();
        iLastAction = best;
        return best;
    }

    @Override
    public void finish(StepContext terminal) {
        if (iLastObs != null && iLastAction >= 0) update(iLastAction, iLastObs, terminal.reward * iRewardScale);
    }

    public long[] pulls() { return iPulls.clone(); }
}
