package org.unitime.timetable.solver.rl;

import java.util.concurrent.TimeUnit;

import org.unitime.timetable.solver.rl.proto.PolicyGrpc;
import org.unitime.timetable.solver.rl.proto.SolverEnvProto;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;

/**
 * Java asks a remote Python {@code Policy} service for the action (python/unitime_rl/serve_policy.py).
 * Used for online / debugging runs where a torch policy is preferred over an ONNX export. Never used
 * in production solves.
 */
public class GrpcPolicy implements PolicyClient {
    private final ManagedChannel iChannel;
    private final PolicyGrpc.PolicyBlockingStub iStub;
    private final long iDeadlineMs;

    public GrpcPolicy(RlConfig cfg) {
        iChannel = ManagedChannelBuilder.forTarget(cfg.grpcTarget).usePlaintext().build();
        iStub = PolicyGrpc.newBlockingStub(iChannel);
        iDeadlineMs = cfg.grpcDeadlineMs;
    }

    @Override
    public int act(StepContext ctx) throws Exception {
        SolverEnvProto.Observation obs = EnvServer.toObservation(ctx.obs, ctx.mask, ctx.metrics, ctx.macroStep, 0);
        SolverEnvProto.Action a = iStub.withDeadlineAfter(iDeadlineMs, TimeUnit.MILLISECONDS).act(obs);
        int action = a.getAction();
        if (action < 0 || action >= ctx.mask.length || !ctx.mask[action]) return PolicyClient.firstAllowed(ctx.mask);
        return action;
    }

    @Override
    public void close() {
        iChannel.shutdownNow();
    }
}
