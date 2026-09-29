package org.unitime.timetable.solver.rl;

import java.util.ArrayList;
import java.util.List;

import org.cpsolver.ifs.util.ToolBox;

/** Diagnostic policies. */
public final class SimplePolicies {
    private SimplePolicies() {}

    /** Uniform over allowed operators. */
    public static class RandomPolicy implements PolicyClient {
        @Override
        public int act(StepContext ctx) {
            List<Integer> allowed = new ArrayList<Integer>();
            for (int i = 0; i < ctx.mask.length; i++) if (ctx.mask[i]) allowed.add(i);
            if (allowed.isEmpty()) return 0;
            return allowed.get(ToolBox.random(allowed.size()));
        }
    }

    /** Always the same operator (masked to the first allowed one if necessary). */
    public static class FixedPolicy implements PolicyClient {
        private final int iAction;
        public FixedPolicy(int action) { iAction = action; }
        @Override
        public int act(StepContext ctx) {
            return (iAction >= 0 && iAction < ctx.mask.length && ctx.mask[iAction]) ? iAction : PolicyClient.firstAllowed(ctx.mask);
        }
        @Override public String name() { return "Fixed(" + Operators.NAMES[iAction] + ")"; }
    }

    /** Round-robin over the allowed operators (a uniform mixture without randomness). */
    public static class RoundRobinPolicy implements PolicyClient {
        private int iNext = 0;
        @Override
        public int act(StepContext ctx) {
            for (int k = 0; k < ctx.mask.length; k++) {
                int a = (iNext + k) % ctx.mask.length;
                if (ctx.mask[a]) { iNext = a + 1; return a; }
            }
            return 0;
        }
    }
}
