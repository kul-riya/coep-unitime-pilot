package org.unitime.timetable.solver.rl;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * Hands control of the macro-step boundary to another thread (the gRPC server). The solver thread
 * posts the boundary (observation, reward, metrics) and blocks until Python replies with an action.
 * When the episode finishes, the environment posts a terminal boundary itself.
 */
public class BridgePolicy implements PolicyClient {

    public static final class Boundary {
        public final float[] obs;
        public final boolean[] mask;
        public final double reward;
        public final SearchMetrics metrics;
        public final int macroStep;
        public final boolean terminated, truncated;

        public Boundary(float[] obs, boolean[] mask, double reward, SearchMetrics metrics, int macroStep, boolean terminated, boolean truncated) {
            this.obs = obs; this.mask = mask; this.reward = reward; this.metrics = metrics;
            this.macroStep = macroStep; this.terminated = terminated; this.truncated = truncated;
        }
    }

    private final LinkedBlockingQueue<Boundary> iToClient = new LinkedBlockingQueue<Boundary>();
    private final LinkedBlockingQueue<Integer> iFromClient = new LinkedBlockingQueue<Integer>();
    private volatile boolean iAborted = false;
    private volatile Boundary iLastBoundary = null;

    @Override
    public int act(StepContext ctx) throws Exception {
        if (iAborted) throw new EpisodeAborted();
        Boundary b = new Boundary(ctx.obs, ctx.mask, ctx.reward, ctx.metrics, ctx.macroStep, false, false);
        iLastBoundary = b;
        iToClient.put(b);
        Integer action = iFromClient.take();
        if (iAborted || action == null || action < 0) throw new EpisodeAborted();
        if (action >= ctx.mask.length || !ctx.mask[action]) return PolicyClient.firstAllowed(ctx.mask);
        return action;
    }

    @Override
    public void finish(StepContext terminal) {
        // the environment posts the terminal boundary with the truncated flag it knows about
    }

    /** Called by the environment when the solver thread has stopped. */
    public void postTerminal(float[] obs, boolean[] mask, double reward, SearchMetrics metrics, int macroStep, boolean truncated) {
        Boundary b = new Boundary(obs, mask, reward, metrics, macroStep, !truncated, truncated);
        iLastBoundary = b;
        iToClient.offer(b);
    }

    /** Python side: deliver the action and wait for the next boundary. */
    public Boundary step(int action, long timeoutMs) throws InterruptedException {
        iFromClient.put(action);
        return iToClient.poll(timeoutMs, TimeUnit.MILLISECONDS);
    }

    /** Python side: wait for the first boundary after reset. */
    public Boundary awaitBoundary(long timeoutMs) throws InterruptedException {
        return iToClient.poll(timeoutMs, TimeUnit.MILLISECONDS);
    }

    public Boundary lastBoundary() { return iLastBoundary; }

    /** Unblock the solver thread; it will stop selecting neighbours. */
    public void abort() {
        iAborted = true;
        iFromClient.offer(-1);
    }

    public boolean isAborted() { return iAborted; }
}
