package org.unitime.timetable.solver.rl;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** One JSON object per line, one line per macro-step. */
public class TrajectoryLogger implements AutoCloseable {
    private static final Logger sLog = LogManager.getLogger(TrajectoryLogger.class);
    private BufferedWriter iWriter;
    private long iLines = 0;

    public TrajectoryLogger(String path) {
        try {
            File f = new File(path);
            if (f.getParentFile() != null) f.getParentFile().mkdirs();
            iWriter = new BufferedWriter(new FileWriter(f, true));
        } catch (IOException e) {
            sLog.warn("Cannot open trajectory log " + path + ": " + e.getMessage());
            iWriter = null;
        }
    }

    public synchronized void log(Map<String, Object> record) {
        if (iWriter == null) return;
        try {
            iWriter.write(Json.write(record));
            iWriter.newLine();
            if (++iLines % 100 == 0) iWriter.flush();
        } catch (IOException e) {
            sLog.warn("trajectory log: " + e.getMessage());
        }
    }

    @Override
    public synchronized void close() {
        if (iWriter == null) return;
        try { iWriter.flush(); iWriter.close(); } catch (IOException e) { /* ignore */ }
        iWriter = null;
    }
}
