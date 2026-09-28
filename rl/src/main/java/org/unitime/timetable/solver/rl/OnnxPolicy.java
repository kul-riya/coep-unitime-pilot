package org.unitime.timetable.solver.rl;

import java.nio.FloatBuffer;
import java.util.Collections;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.ifs.util.ToolBox;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;

/**
 * In-JVM inference with ONNX Runtime. The graph takes {@code obs [1, 48]} and returns
 * {@code logits [1, 8]}; the mask and the argmax (or sampling) are applied here. Any failure creating
 * the session or running the forward pass propagates to {@link RlNeighbourSelection}, which flips the
 * run to the default selector.
 */
public class OnnxPolicy implements PolicyClient {
    private static final Logger sLog = LogManager.getLogger(OnnxPolicy.class);
    private final OrtEnvironment iEnv;
    private final OrtSession iSession;
    private final String iInputName;
    private final boolean iStochastic;
    private final double iTimeoutNs;
    private final int iMaxSlowCalls;
    private int iSlowCalls = 0;
    private long iCalls = 0, iTotalNs = 0;

    public OnnxPolicy(RlConfig cfg) throws Exception {
        if (cfg.onnxPath == null) throw new IllegalArgumentException("Rl.Onnx.Path is not set");
        iEnv = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
        opts.setIntraOpNumThreads(1);
        opts.setInterOpNumThreads(1);
        iSession = iEnv.createSession(cfg.onnxPath, opts);
        iInputName = iSession.getInputNames().iterator().next();
        iStochastic = cfg.onnxStochastic;
        iTimeoutNs = cfg.onnxTimeoutMs * 1e6;
        iMaxSlowCalls = cfg.onnxMaxSlowCalls;
        // warm-up so the first real call is not the slow one
        forward(new float[StateEncoder.DIM]);
        sLog.info("ONNX policy loaded from " + cfg.onnxPath + " (input=" + iInputName + ")");
    }

    private float[] forward(float[] obs) throws Exception {
        try (OnnxTensor t = OnnxTensor.createTensor(iEnv, FloatBuffer.wrap(obs), new long[] {1, obs.length});
             OrtSession.Result r = iSession.run(Collections.singletonMap(iInputName, t))) {
            float[][] out = (float[][]) r.get(0).getValue();
            return out[0];
        }
    }

    @Override
    public int act(StepContext ctx) throws Exception {
        long t0 = System.nanoTime();
        float[] logits = forward(ctx.obs);
        long dt = System.nanoTime() - t0;
        iCalls++; iTotalNs += dt;
        if (dt > iTimeoutNs) {
            iSlowCalls++;
            if (iSlowCalls >= iMaxSlowCalls)
                throw new IllegalStateException("ONNX forward pass exceeded " + (iTimeoutNs / 1e6) + " ms on " + iSlowCalls + " calls");
        }
        return iStochastic ? PolicyClient.sampleMasked(logits, ctx.mask, ToolBox.random()) : PolicyClient.argmaxMasked(logits, ctx.mask);
    }

    public double meanForwardMs() { return iCalls == 0 ? 0 : iTotalNs / 1e6 / iCalls; }

    @Override
    public void close() {
        try { iSession.close(); } catch (Exception e) { sLog.warn("closing ONNX session: " + e.getMessage()); }
        sLog.info("ONNX policy: " + iCalls + " calls, mean " + String.format("%.3f", meanForwardMs()) + " ms, slow=" + iSlowCalls);
    }
}
