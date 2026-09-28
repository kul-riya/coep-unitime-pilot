package org.unitime.timetable.solver.rl;

import java.io.File;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.ifs.util.DataProperties;
import org.cpsolver.ifs.util.ToolBox;
import org.unitime.timetable.solver.rl.proto.SolverEnvGrpc;
import org.unitime.timetable.solver.rl.proto.SolverEnvProto;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

/**
 * gRPC training environment: {@code Reset(InstanceId) -> Observation},
 * {@code Step(Action) -> (Observation, reward, terminated, truncated, mask)}.
 *
 * <pre>
 * java -cp unitime-rl-all.jar org.unitime.timetable.solver.rl.EnvServer \
 *      --port 50051 --instances rl/instances --config rl/config/unitime-coep-default.properties [--config more]
 * </pre>
 *
 * One server = one worker = one resident model. Run several servers on different ports for parallel
 * environments; a crash in one worker stays inside that worker.
 */
public class EnvServer extends SolverEnvGrpc.SolverEnvImplBase {
    private static final Logger sLog = LogManager.getLogger(EnvServer.class);

    private final DataProperties iProperties;
    private final File iInstanceDir;
    private final long iStepTimeoutMs;
    private final Map<String, SolverEnvironment> iEnvironments = new HashMap<String, SolverEnvironment>();
    private SolverEnvironment iCurrent = null;
    private Server iServer;

    public EnvServer(DataProperties properties, File instanceDir, long stepTimeoutMs) {
        iProperties = properties;
        iInstanceDir = instanceDir;
        iStepTimeoutMs = stepTimeoutMs;
    }

    private synchronized SolverEnvironment environment(String instance) throws Exception {
        if (instance == null || instance.isEmpty()) {
            if (iCurrent == null) throw new IllegalArgumentException("no instance loaded yet; Reset must name one");
            return iCurrent;
        }
        SolverEnvironment env = iEnvironments.get(instance);
        if (env == null) {
            File f = new File(instance);
            if (!f.exists()) f = new File(iInstanceDir, instance);
            if (!f.exists()) f = new File(iInstanceDir, instance + ".xml");
            if (!f.exists()) throw new IllegalArgumentException("instance not found: " + instance);
            env = new SolverEnvironment(iProperties, f);
            iEnvironments.put(instance, env);
        }
        if (iCurrent != null && iCurrent != env) iCurrent.stop();
        iCurrent = env;
        return env;
    }

    static SolverEnvProto.Metrics toMetrics(SearchMetrics m, int macroStep, long committed) {
        SolverEnvProto.Metrics.Builder b = SolverEnvProto.Metrics.newBuilder();
        if (m == null) return b.build();
        b.setStudentViolationRate(m.studentViolationRate())
         .setCheckerViolationRate(m.conflicts.checkerViolationRate())
         .setPairViolationRate(m.conflicts.pairViolationRate())
         .setAssignedRatio(m.assignedRatio)
         .setHardViolations(m.hardViolations)
         .setSoftPenalty(m.softPenalty)
         .setSoftPenaltyNorm(m.softPenaltyNorm)
         .setTotalValue(m.totalValue)
         .setPotential(m.potential)
         .setIteration(m.iteration)
         .setMacroStep(macroStep)
         .setTimeSec(m.timeSec)
         .setCommitted(committed);
        for (Map.Entry<String, Object> e: m.toMap().entrySet())
            if (e.getValue() instanceof Number) b.putExtra(e.getKey(), ((Number) e.getValue()).doubleValue());
        return b.build();
    }

    static SolverEnvProto.Observation toObservation(float[] obs, boolean[] mask, SearchMetrics m, int macroStep, long committed) {
        SolverEnvProto.Observation.Builder b = SolverEnvProto.Observation.newBuilder();
        for (float f: obs) b.addFeatures(f);
        for (boolean x: mask) b.addActionMask(x);
        b.setMetrics(toMetrics(m, macroStep, committed));
        return b.build();
    }

    private SolverEnvProto.Observation observation(BridgePolicy.Boundary b, SolverEnvironment env) {
        long committed = env.getRuntime() == null ? 0 : env.getRuntime().getCommitted();
        return toObservation(b.obs, b.mask, b.metrics, b.macroStep, committed);
    }

    @Override
    public void reset(SolverEnvProto.InstanceId request, StreamObserver<SolverEnvProto.Observation> out) {
        try {
            SolverEnvironment env = environment(request.getInstance());
            BridgePolicy.Boundary b = env.reset(request.getSeed(), request.getPropertiesMap(), iStepTimeoutMs);
            out.onNext(observation(b, env));
            out.onCompleted();
        } catch (Exception e) {
            sLog.error("Reset failed: " + e.getMessage(), e);
            out.onError(Status.INTERNAL.withDescription(String.valueOf(e.getMessage())).withCause(e).asRuntimeException());
        }
    }

    @Override
    public void step(SolverEnvProto.Action request, StreamObserver<SolverEnvProto.StepResult> out) {
        try {
            SolverEnvironment env = iCurrent;
            if (env == null) throw new IllegalStateException("Reset first");
            BridgePolicy.Boundary b = env.step(request.getAction(), iStepTimeoutMs);
            if (b == null) throw new IllegalStateException("no boundary within " + iStepTimeoutMs + " ms (solver stuck?)");
            SolverEnvProto.StepResult.Builder r = SolverEnvProto.StepResult.newBuilder()
                    .setObservation(observation(b, env))
                    .setReward(b.reward)
                    .setTerminated(b.terminated)
                    .setTruncated(b.truncated);
            if (b.metrics != null) {
                r.putInfo("assigned_ratio", String.valueOf(b.metrics.assignedRatio));
                r.putInfo("student_violation_rate", String.valueOf(b.metrics.studentViolationRate()));
            }
            out.onNext(r.build());
            out.onCompleted();
        } catch (Exception e) {
            sLog.error("Step failed: " + e.getMessage(), e);
            out.onError(Status.INTERNAL.withDescription(String.valueOf(e.getMessage())).withCause(e).asRuntimeException());
        }
    }

    @Override
    public void info(SolverEnvProto.Empty request, StreamObserver<SolverEnvProto.Metrics> out) {
        try {
            SolverEnvironment env = iCurrent;
            SearchMetrics m = env == null ? null : env.currentMetrics();
            out.onNext(toMetrics(m, env == null || env.getSelection() == null ? 0 : env.getSelection().getMacroStep(),
                    env == null || env.getRuntime() == null ? 0 : env.getRuntime().getCommitted()));
            out.onCompleted();
        } catch (Exception e) {
            out.onError(Status.INTERNAL.withDescription(String.valueOf(e.getMessage())).asRuntimeException());
        }
    }

    @Override
    public void save(SolverEnvProto.SavePath request, StreamObserver<SolverEnvProto.Empty> out) {
        try {
            if (iCurrent == null) throw new IllegalStateException("Reset first");
            iCurrent.save(new File(request.getPath()));
            out.onNext(SolverEnvProto.Empty.getDefaultInstance());
            out.onCompleted();
        } catch (Exception e) {
            out.onError(Status.INTERNAL.withDescription(String.valueOf(e.getMessage())).asRuntimeException());
        }
    }

    @Override
    public void close(SolverEnvProto.Empty request, StreamObserver<SolverEnvProto.Empty> out) {
        try {
            if (iCurrent != null) iCurrent.stop();
            out.onNext(SolverEnvProto.Empty.getDefaultInstance());
            out.onCompleted();
        } catch (Exception e) {
            out.onError(Status.INTERNAL.withDescription(String.valueOf(e.getMessage())).asRuntimeException());
        }
    }

    public void start(int port) throws Exception {
        iServer = ServerBuilder.forPort(port).addService(this).build().start();
        sLog.info("SolverEnv listening on port " + port + ", instances in " + iInstanceDir);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try { stop(); } catch (Exception e) { /* ignore */ }
        }));
    }

    public void stop() throws Exception {
        if (iCurrent != null) iCurrent.stop();
        if (iServer != null) iServer.shutdown().awaitTermination(5, TimeUnit.SECONDS);
    }

    public void blockUntilShutdown() throws InterruptedException {
        if (iServer != null) iServer.awaitTermination();
    }

    public static void main(String[] args) throws Exception {
        int port = 50051;
        File instances = new File("rl/instances");
        long stepTimeoutMs = 600000;
        DataProperties p = new DataProperties();
        boolean logging = true;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--port": port = Integer.parseInt(args[++i]); break;
                case "--instances": instances = new File(args[++i]); break;
                case "--config": p.putAll(ToolBox.loadProperties(new File(args[++i]))); break;
                case "--step-timeout-ms": stepTimeoutMs = Long.parseLong(args[++i]); break;
                case "--set": { String kv = args[++i]; int eq = kv.indexOf('='); p.setProperty(kv.substring(0, eq), kv.substring(eq + 1)); break; }
                case "--no-log": logging = false; break;
                default: throw new IllegalArgumentException("unknown argument " + args[i]);
            }
        }
        if (logging) ToolBox.setupLogging(new File("envserver-" + port + ".log"), false);
        p.setProperty("General.Save", "false");
        p.setProperty("Xml.ShowNames", "true");
        p.setProperty("Xml.ExportStudentSectioning", "true");
        EnvServer server = new EnvServer(p, instances, stepTimeoutMs);
        server.start(port);
        server.blockUntilShutdown();
    }
}
