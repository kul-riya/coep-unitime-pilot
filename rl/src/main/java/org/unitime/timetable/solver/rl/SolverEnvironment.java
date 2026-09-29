package org.unitime.timetable.solver.rl;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.coursett.TimetableXMLLoader;
import org.cpsolver.coursett.TimetableXMLSaver;
import org.cpsolver.coursett.constraint.JenrlConstraint;
import org.cpsolver.coursett.model.Configuration;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.Student;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.assignment.DefaultSingleAssignment;
import org.cpsolver.ifs.extension.Extension;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.util.DataProperties;

/**
 * One resident timetable instance that can be solved many times. The XML is loaded once; a reset
 * restores the stored initial assignment and student sectioning in memory (no Hibernate, no reload)
 * and starts a fresh {@link Solver} with a {@link RlNeighbourSelection} driven by a {@link BridgePolicy}.
 */
public class SolverEnvironment {
    private static final Logger sLog = LogManager.getLogger(SolverEnvironment.class);

    private final DataProperties iBaseProperties;
    private final File iInputFile;
    private TimetableModel iModel;
    private Assignment<Lecture, Placement> iAssignment;
    private Map<Lecture, Placement> iInitialPlacements;
    private Map<Student, Set<Lecture>> iInitialEnrollment;

    private Solver<Lecture, Placement> iSolver;
    private Solution<Lecture, Placement> iSolution;
    private RlNeighbourSelection iSelection;
    private BridgePolicy iBridge;
    private RlRuntime iRuntime;
    private Thread iWatcher;
    private int iEpisodes = 0;

    public SolverEnvironment(DataProperties baseProperties, File inputFile) throws Exception {
        iBaseProperties = baseProperties;
        iInputFile = inputFile;
        load();
    }

    public TimetableModel getModel() { return iModel; }
    public File getInputFile() { return iInputFile; }
    public BridgePolicy getBridge() { return iBridge; }
    public RlNeighbourSelection getSelection() { return iSelection; }
    public Solution<Lecture, Placement> getSolution() { return iSolution; }
    public RlRuntime getRuntime() { return iRuntime; }
    public int getEpisodes() { return iEpisodes; }

    private void load() throws Exception {
        DataProperties p = new DataProperties(iBaseProperties);
        p.setProperty("General.Input", iInputFile.getPath());
        iModel = new TimetableModel(p);
        iAssignment = new DefaultSingleAssignment<Lecture, Placement>();
        TimetableXMLLoader loader = new TimetableXMLLoader(iModel, iAssignment);
        loader.setInputFile(iInputFile);
        loader.load();
        iInitialPlacements = new HashMap<Lecture, Placement>();
        for (Lecture lecture: iModel.variables()) {
            Placement pl = iAssignment.getValue(lecture);
            if (pl != null) iInitialPlacements.put(lecture, pl);
        }
        iInitialEnrollment = snapshotEnrollment();
        sLog.info("Loaded " + iInputFile.getName() + ": " + iModel.variables().size() + " classes, " + iModel.getAllStudents().size()
                + " students, " + iInitialPlacements.size() + " initially assigned");
        if (iModel.getAllStudents().isEmpty())
            sLog.warn("instance " + iInputFile.getName() + " has no students: the reward has no conflict signal. Export it from a solver "
                    + "loaded with 'Student Course Demands' = 'Enrolled Student Course Demands'.");
    }

    private Map<Student, Set<Lecture>> snapshotEnrollment() {
        Map<Student, Set<Lecture>> map = new HashMap<Student, Set<Lecture>>();
        for (Student s: iModel.getAllStudents()) map.put(s, new HashSet<Lecture>(s.getLectures()));
        return map;
    }

    /** Restore the initial assignment and the initial student sectioning. */
    private void restoreInitial() {
        for (Lecture lecture: iModel.variables())
            if (iAssignment.getValue(lecture) != null) iAssignment.unassign(0, lecture);
        restoreEnrollment(iInitialEnrollment);
        int skipped = 0;
        for (Map.Entry<Lecture, Placement> e: iInitialPlacements.entrySet()) {
            Placement pl = e.getValue();
            if (!iModel.conflictValues(iAssignment, pl).isEmpty()) { skipped++; continue; }
            iAssignment.assign(0, pl);
        }
        if (skipped > 0) sLog.warn("restoreInitial: " + skipped + " initial placements skipped due to conflicts");
        iModel.clearBest();
    }

    /** Same algorithm as TimetableModel.restoreBest for enrollments, on an arbitrary snapshot. */
    private void restoreEnrollment(Map<Student, Set<Lecture>> target) {
        for (Map.Entry<Student, Set<Lecture>> entry: target.entrySet()) {
            Student student = entry.getKey();
            Set<Lecture> lectures = entry.getValue();
            if (student.getLectures().equals(lectures)) continue;
            Set<Configuration> configs = new HashSet<Configuration>();
            for (Lecture l: lectures) if (l.getConfiguration() != null) configs.add(l.getConfiguration());
            for (Lecture lecture: new ArrayList<Lecture>(student.getLectures())) {
                if (lectures.contains(lecture)) continue;
                for (Lecture other: student.getLectures()) decJenrl(student, lecture, other);
                lecture.removeStudent(iAssignment, student);
                student.removeLecture(lecture);
                if (lecture.getConfiguration() != null && !configs.contains(lecture.getConfiguration()))
                    student.removeConfiguration(lecture.getConfiguration());
            }
            for (Lecture lecture: lectures) {
                if (student.getLectures().contains(lecture)) continue;
                for (Lecture other: student.getLectures()) incJenrl(student, lecture, other);
                lecture.addStudent(iAssignment, student);
                student.addLecture(lecture);
                if (lecture.getConfiguration() != null) student.addConfiguration(lecture.getConfiguration());
            }
        }
    }

    private void incJenrl(Student student, Lecture l1, Lecture l2) {
        if (l1.equals(l2)) return;
        JenrlConstraint jenrl = l1.jenrlConstraint(l2);
        if (jenrl == null) {
            jenrl = new JenrlConstraint();
            jenrl.addVariable(l1);
            jenrl.addVariable(l2);
            iModel.addConstraint(jenrl);
        }
        jenrl.incJenrl(iAssignment, student);
    }

    private void decJenrl(Student student, Lecture l1, Lecture l2) {
        if (l1.equals(l2)) return;
        JenrlConstraint jenrl = l1.jenrlConstraint(l2);
        if (jenrl != null) jenrl.decJenrl(iAssignment, student);
    }

    /** Stop a running episode (if any), restore the initial solution and start a new solver. */
    public synchronized BridgePolicy.Boundary reset(long seed, Map<String, String> overrides, long timeoutMs) throws Exception {
        stop();
        restoreInitial();
        DataProperties p = new DataProperties(iBaseProperties);
        p.setProperty("General.Input", iInputFile.getPath());
        p.setProperty("General.Save", "false");
        p.setProperty("Parallel.NrSolvers", "1");
        p.setProperty("Neighbour.Class", RlNeighbourSelection.class.getName());
        p.setProperty("Termination.Class", RlTerminationCondition.class.getName());
        if (p.getProperty("Comparator.Class") == null || "native".equalsIgnoreCase(p.getProperty("Rl.Comparator", "lex")))
            p.setProperty("Comparator.Class", "lex".equalsIgnoreCase(p.getProperty("Rl.Comparator", "lex")) ? LexicographicComparator.class.getName() : "org.cpsolver.coursett.heuristics.TimetableComparator");
        else
            p.setProperty("Comparator.Class", LexicographicComparator.class.getName());
        p.setProperty("Rl.Policy", "bridge");
        p.setProperty("Rl.Mode", "act");
        p.setProperty("General.SearchIntensification", "false");
        p.setProperty("General.CompleteSolutionFixInterval", "-1");
        p.setProperty("General.IncompleteSolutionFixInterval", "-1");
        if (seed != 0) p.setProperty("General.Seed", String.valueOf(seed));
        if (overrides != null) for (Map.Entry<String, String> e: overrides.entrySet()) p.setProperty(e.getKey(), e.getValue());
        p.expand();

        RlConfig cfg = new RlConfig(p);
        iRuntime = RlRuntime.getOrCreate(iModel, cfg);
        iBridge = new BridgePolicy();
        iRuntime.setExternalPolicy(iBridge);
        iSolution = new Solution<Lecture, Placement>(iModel, iAssignment);
        iSolver = new Solver<Lecture, Placement>(p);
        iSolver.setInitalSolution(iSolution);
        // note: the loader may have registered the model's Progress; nothing else to reset
        iSolver.start();
        final Solver<Lecture, Placement> solver = iSolver;
        final BridgePolicy bridge = iBridge;
        iWatcher = new Thread(() -> watch(solver, bridge), "EnvWatcher");
        iWatcher.setDaemon(true);
        iWatcher.start();
        iEpisodes++;
        BridgePolicy.Boundary first = iBridge.awaitBoundary(timeoutMs);
        if (first == null) throw new IllegalStateException("solver did not reach the first macro-step boundary within " + timeoutMs + " ms");
        iSelection = (RlNeighbourSelection) solver.getNeighbourSelection();
        return first;
    }

    /** Wait for the solver thread; then compute terminal metrics and post the terminal boundary. */
    private void watch(Solver<Lecture, Placement> solver, BridgePolicy bridge) {
        try {
            Thread t = solver.getSolverThread();
            if (t != null) t.join();
        } catch (InterruptedException e) {
            return;
        }
        synchronized (this) {
            try {
                RlNeighbourSelection sel = (RlNeighbourSelection) solver.getNeighbourSelection();
                Solution<Lecture, Placement> sol = solver.lastSolution() == null ? solver.currentSolution() : solver.lastSolution();
                if (sol.getBestInfo() != null) sol.restoreBest();
                SearchMetrics terminal = sel == null ? null : sel.finish(sol);
                double reward = sel == null || terminal == null ? 0.0 : sel.terminalReward(terminal);
                if (terminal == null) {
                    ConflictReport r = iRuntime.oracle.evaluate(sol.getAssignment());
                    terminal = SearchMetrics.compute(iModel, sol.getAssignment(), r, iRuntime.config, iRuntime.scales, true, sol.getIteration(), sol.getTime());
                }
                StateEncoder.Dynamics d = new StateEncoder.Dynamics();
                d.progress = 1.0;
                float[] obs = StateEncoder.encode(terminal, iRuntime.scales, d, iRuntime.config);
                boolean[] mask = new boolean[Operators.COUNT];
                java.util.Arrays.fill(mask, true);
                boolean truncated = sel != null && (sel.isTruncated() || bridge.isAborted());
                bridge.postTerminal(obs, mask, reward, terminal, sel == null ? 0 : sel.getMacroStep(), truncated);
            } catch (Exception e) {
                sLog.error("terminal bookkeeping failed: " + e.getMessage(), e);
                bridge.postTerminal(new float[StateEncoder.DIM], new boolean[Operators.COUNT], 0.0, null, 0, true);
            }
        }
    }

    /** Deliver an action and wait for the next boundary (or the terminal one). */
    public BridgePolicy.Boundary step(int action, long timeoutMs) throws InterruptedException {
        if (iBridge == null) throw new IllegalStateException("reset() first");
        return iBridge.step(action, timeoutMs);
    }

    /** Stop the running solver, if any, and release listeners. */
    public synchronized void stop() {
        if (iSolver == null) return;
        if (iBridge != null) iBridge.abort();
        try {
            iSolver.stopSolver(true);
        } catch (Exception e) {
            sLog.warn("stopSolver: " + e.getMessage());
        }
        if (iWatcher != null) { try { iWatcher.join(5000); } catch (InterruptedException e) { /* ignore */ } }
        if (iSelection != null) iSelection.dispose();
        else if (iSolver.getNeighbourSelection() instanceof RlNeighbourSelection) ((RlNeighbourSelection) iSolver.getNeighbourSelection()).dispose();
        for (Extension<Lecture, Placement> ext: new ArrayList<Extension<Lecture, Placement>>(iSolver.getExtensions())) ext.unregister(iModel);
        if (iRuntime != null) iRuntime.detach();
        if (iSolver.getNeighbourSelection() != null && iSolution != null) {
            List<org.cpsolver.ifs.solution.SolutionListener<Lecture, Placement>> ls = new ArrayList<org.cpsolver.ifs.solution.SolutionListener<Lecture, Placement>>(iSolution.getSolutionListeners());
            for (org.cpsolver.ifs.solution.SolutionListener<Lecture, Placement> l: ls) iSolution.removeSolutionListener(l);
        }
        iSolver.dispose();
        iSolver = null;
        iSelection = null;
        iWatcher = null;
    }

    public SearchMetrics currentMetrics() {
        if (iRuntime == null) return null;
        Solution<Lecture, Placement> sol = iSolution;
        if (sol == null) return null;
        ConflictReport r = iRuntime.oracle.evaluate(sol.getAssignment());
        return SearchMetrics.compute(iModel, sol.getAssignment(), r, iRuntime.config, iRuntime.scales, true, sol.getIteration(), sol.getTime());
    }

    public synchronized void save(File file) throws Exception {
        if (iSolver == null) throw new IllegalStateException("no solver");
        TimetableXMLSaver saver = new TimetableXMLSaver(iSolver);
        saver.save(file);
    }
}
