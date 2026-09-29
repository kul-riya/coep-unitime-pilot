package org.unitime.timetable.solver.rl;

/**
 * Chooses an operator at a macro-step boundary. Implementations: {@link OnnxPolicy} (in-JVM
 * inference), {@link GrpcPolicy} (remote Python policy), {@link BridgePolicy} (Python owns the
 * episode; used by {@link EnvServer}), {@link LinUcbPolicy} (contextual bandit control arm),
 * {@link RandomPolicy} and {@link FixedPolicy} (diagnostics).
 */
public interface PolicyClient extends AutoCloseable {

    /** Everything known at a boundary. {@code reward} is the reward of the step that just ended. */
    final class StepContext {
        public float[] obs;
        public boolean[] mask;
        public double reward;
        public SearchMetrics metrics;
        public int macroStep;
        public int previousAction;
        public boolean firstStep;
    }

    /** @return operator id in [0, Operators.COUNT) that is allowed by {@code ctx.mask} */
    int act(StepContext ctx) throws Exception;

    /** Called once when the episode ends (solver stopped), with the terminal reward. */
    default void finish(StepContext terminal) {}

    default String name() { return getClass().getSimpleName(); }

    @Override
    default void close() {}

    /** Thrown by {@link BridgePolicy} when the episode is reset while the solver waits for an action. */
    final class EpisodeAborted extends RuntimeException {
        private static final long serialVersionUID = 1L;
        public EpisodeAborted() { super("episode aborted"); }
    }

    static int firstAllowed(boolean[] mask) {
        for (int i = 0; i < mask.length; i++) if (mask[i]) return i;
        return 0;
    }

    static int argmaxMasked(float[] logits, boolean[] mask) {
        int best = -1;
        for (int i = 0; i < logits.length; i++) {
            if (!mask[i]) continue;
            if (best < 0 || logits[i] > logits[best]) best = i;
        }
        return best < 0 ? firstAllowed(mask) : best;
    }

    static int sampleMasked(float[] logits, boolean[] mask, double u) {
        double max = Double.NEGATIVE_INFINITY;
        for (int i = 0; i < logits.length; i++) if (mask[i]) max = Math.max(max, logits[i]);
        if (max == Double.NEGATIVE_INFINITY) return firstAllowed(mask);
        double[] p = new double[logits.length];
        double z = 0;
        for (int i = 0; i < logits.length; i++) if (mask[i]) { p[i] = Math.exp(logits[i] - max); z += p[i]; }
        double acc = 0;
        for (int i = 0; i < logits.length; i++) {
            if (!mask[i]) continue;
            acc += p[i] / z;
            if (u <= acc) return i;
        }
        return argmaxMasked(logits, mask);
    }
}
