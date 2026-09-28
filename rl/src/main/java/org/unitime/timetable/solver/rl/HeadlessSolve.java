package org.unitime.timetable.solver.rl;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.cpsolver.coursett.TimetableXMLLoader;
import org.cpsolver.coursett.TimetableXMLSaver;
import org.cpsolver.coursett.heuristics.FixCompleteSolutionNeighbourSelection;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.algorithms.SimpleSearch;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.assignment.DefaultSingleAssignment;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.util.DataProperties;
import org.cpsolver.ifs.util.Progress;
import org.cpsolver.ifs.util.ProgressWriter;
import org.cpsolver.ifs.util.ToolBox;

/**
 * Headless bake-off runner: one arm, one instance, one seed, one budget; writes metrics.json.
 *
 * <pre>
 * java -jar unitime-rl-all.jar --config rl/config/unitime-coep-default.properties \
 *      --input instance.xml --out runs/B0/seed1 --arm B0 --seed 1 --timeout 600
 * </pre>
 *
 * Arms: B0 (stock IFS), B1 (B0 with --student-conflict-weight), B2 (Great Deluge with
 * RandomStudentSwap and Suggestion), L (LinUCB over the eight operators), R (frozen ONNX policy),
 * SHADOW (default selector executes, policy logged), RANDOM / ROUNDROBIN / FIXED (diagnostics).
 */
public class HeadlessSolve {
    private static final Logger sLog = LogManager.getLogger(HeadlessSolve.class);

    public static class Options {
        public List<String> configs = new ArrayList<String>();
        public String input, out = "out", arm = "B0", onnx = null, comparator = null;
        public long seed = 1;
        public double timeout = -1;
        public long maxIters = -1, maxCommitted = -1;
        public int k = -1, maxMacroSteps = -1;
        public Double studentConflictWeight = null, hardStudentConflictWeight = null;
        public boolean saveSolution = false, writeScales = false, trajectory = true, quiet = false, requireStudents = false;
        public Map<String, String> set = new LinkedHashMap<String, String>();
    }

    public static Options parse(String[] args) {
        Options o = new Options();
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            switch (a) {
                case "--config": o.configs.add(args[++i]); break;
                case "--input": o.input = args[++i]; break;
                case "--out": o.out = args[++i]; break;
                case "--arm": o.arm = args[++i].toUpperCase(); break;
                case "--seed": o.seed = Long.parseLong(args[++i]); break;
                case "--timeout": o.timeout = Double.parseDouble(args[++i]); break;
                case "--max-iters": o.maxIters = Long.parseLong(args[++i]); break;
                case "--max-committed": o.maxCommitted = Long.parseLong(args[++i]); break;
                case "--max-macro-steps": o.maxMacroSteps = Integer.parseInt(args[++i]); break;
                case "--k": o.k = Integer.parseInt(args[++i]); break;
                case "--onnx": o.onnx = args[++i]; break;
                case "--comparator": o.comparator = args[++i]; break;
                case "--student-conflict-weight": o.studentConflictWeight = Double.valueOf(args[++i]); break;
                case "--hard-student-conflict-weight": o.hardStudentConflictWeight = Double.valueOf(args[++i]); break;
                case "--save-solution": o.saveSolution = true; break;
                case "--write-scales": o.writeScales = true; break;
                case "--no-trajectory": o.trajectory = false; break;
                case "--quiet": o.quiet = true; break;
                case "--require-students": o.requireStudents = true; break;
                case "--set": { String kv = args[++i]; int eq = kv.indexOf('='); o.set.put(kv.substring(0, eq), kv.substring(eq + 1)); break; }
                case "--help": usage(); System.exit(0);
                default: throw new IllegalArgumentException("unknown argument " + a);
            }
        }
        if (o.input == null) { usage(); throw new IllegalArgumentException("--input is required"); }
        return o;
    }

    private static void usage() {
        System.out.println("HeadlessSolve --input model.xml [--config a.properties]... --arm B0|B1|B2|L|R|SHADOW|RANDOM|ROUNDROBIN|FIXED\n"
                + "  --out DIR --seed N --timeout SEC --max-iters N --max-committed N --max-macro-steps N --k N\n"
                + "  --student-conflict-weight W --hard-student-conflict-weight W --onnx policy.onnx --comparator native|lex\n"
                + "  --save-solution --write-scales --no-trajectory --require-students --set Key=Value");
    }

    /** Solver properties for an arm, layered over the configuration files. */
    public static DataProperties properties(Options o) throws Exception {
        DataProperties p = new DataProperties();
        for (String cfg: o.configs) {
            DataProperties layer = ToolBox.loadProperties(new File(cfg));
            p.putAll(layer);
        }
        p.setProperty("General.Input", o.input);
        p.setProperty("General.Output", o.out);
        p.setProperty("General.Seed", String.valueOf(o.seed));
        p.setProperty("General.Save", "false");
        p.setProperty("Xml.ShowNames", "true");
        p.setProperty("Xml.ExportStudentSectioning", "true");
        p.setProperty("Parallel.NrSolvers", "1");
        p.setProperty("Termination.Class", RlTerminationCondition.class.getName());
        if (o.timeout >= 0) p.setProperty("Termination.TimeOut", String.valueOf(o.timeout));
        if (o.maxIters >= 0) p.setProperty("Termination.MaxIters", String.valueOf(o.maxIters));
        if (o.maxCommitted >= 0) p.setProperty("Rl.MaxCommitted", String.valueOf(o.maxCommitted));
        if (o.maxMacroSteps >= 0) p.setProperty("Rl.MaxMacroSteps", String.valueOf(o.maxMacroSteps));
        if (o.k > 0) p.setProperty("Rl.K", String.valueOf(o.k));
        // The student-conflict weight appears in three selection stages of the stock solver with the same
        // stock value (0.2): the solution comparator / acceptance, the variable selection and the value
        // selection. The sweep moves them together so acceptance and proposal stay consistent.
        if (o.studentConflictWeight != null) {
            String w = String.valueOf(o.studentConflictWeight);
            p.setProperty("Comparator.StudentConflictWeight", w);
            p.setProperty("Lecture.StudentConflictWeight", w);
            p.setProperty("Placement.NrStudConfsWeight2", w);
        }
        if (o.hardStudentConflictWeight != null) {
            String w = String.valueOf(o.hardStudentConflictWeight);
            p.setProperty("Comparator.HardStudentConflictWeight", w);
            p.setProperty("Lecture.HardStudentConflictWeight", w);
            p.setProperty("Placement.NrHardStudConfsWeight2", w);
        }
        if (o.onnx != null) p.setProperty("Rl.Onnx.Path", o.onnx);
        if (o.trajectory) p.setProperty("Rl.TrajectoryLog", new File(o.out, "trajectory.jsonl").getPath());

        String comparator = o.comparator;
        switch (o.arm) {
            case "B0":
            case "B1":
                p.setProperty("Neighbour.Class", FixCompleteSolutionNeighbourSelection.class.getName());
                if (comparator == null) comparator = "native";
                break;
            case "B2":
                p.setProperty("Neighbour.Class", SimpleSearch.class.getName());
                p.setProperty("Search.GreatDeluge", "true");
                p.setProperty("General.SearchIntensification", "false");
                p.setProperty("General.CompleteSolutionFixInterval", "-1");
                p.setProperty("General.IncompleteSolutionFixInterval", "-1");
                p.setProperty("GreatDeluge.AdditionalNeighbours", p.getProperty("GreatDeluge.AdditionalNeighbours", "")
                        + ";org.cpsolver.coursett.sectioning.RandomStudentSwap;org.cpsolver.coursett.neighbourhoods.Suggestion@0.01");
                p.setProperty("HillClimber.AdditionalNeighbours", p.getProperty("HillClimber.AdditionalNeighbours", "")
                        + ";org.cpsolver.coursett.sectioning.RandomStudentSwap;org.cpsolver.coursett.neighbourhoods.Suggestion@0.01");
                if (comparator == null) comparator = "native";
                break;
            case "L":
                rl(p); p.setProperty("Rl.Policy", "linucb"); p.setProperty("Rl.Mode", "act");
                if (comparator == null) comparator = "lex";
                break;
            case "R":
                rl(p); p.setProperty("Rl.Policy", "onnx"); p.setProperty("Rl.Mode", "act");
                if (comparator == null) comparator = "lex";
                break;
            case "SHADOW":
                rl(p); p.setProperty("Rl.Policy", o.onnx != null ? "onnx" : "none"); p.setProperty("Rl.Mode", "shadow");
                if (comparator == null) comparator = "native";
                break;
            case "RANDOM":
                rl(p); p.setProperty("Rl.Policy", "random"); p.setProperty("Rl.Mode", "act");
                if (comparator == null) comparator = "lex";
                break;
            case "ROUNDROBIN":
                rl(p); p.setProperty("Rl.Policy", "roundrobin"); p.setProperty("Rl.Mode", "act");
                if (comparator == null) comparator = "lex";
                break;
            case "FIXED":
                rl(p); p.setProperty("Rl.Policy", "fixed"); p.setProperty("Rl.Mode", "act");
                if (comparator == null) comparator = "lex";
                break;
            default:
                throw new IllegalArgumentException("unknown arm " + o.arm);
        }
        if ("lex".equalsIgnoreCase(comparator)) p.setProperty("Comparator.Class", LexicographicComparator.class.getName());
        else if (p.getProperty("Comparator.Class") == null) p.setProperty("Comparator.Class", "org.cpsolver.coursett.heuristics.TimetableComparator");
        for (Map.Entry<String, String> e: o.set.entrySet()) p.setProperty(e.getKey(), e.getValue());
        p.expand();
        return p;
    }

    private static void rl(DataProperties p) {
        p.setProperty("Neighbour.Class", RlNeighbourSelection.class.getName());
        p.setProperty("General.SearchIntensification", "false");
        p.setProperty("General.CompleteSolutionFixInterval", "-1");
        p.setProperty("General.IncompleteSolutionFixInterval", "-1");
    }

    /** Result of one run. */
    public static class Result {
        public Map<String, Object> metrics = new LinkedHashMap<String, Object>();
        public SearchMetrics finalMetrics;
        public SearchMetrics initialMetrics;
    }

    public static Result run(Options o) throws Exception {
        DataProperties properties = properties(o);
        File outDir = new File(o.out);
        outDir.mkdirs();
        if (!o.quiet) ToolBox.setupLogging(new File(outDir, "debug.log"), false);
        RlConfig cfg = new RlConfig(properties);

        TimetableModel model = new TimetableModel(properties);
        Assignment<Lecture, Placement> assignment = new DefaultSingleAssignment<Lecture, Placement>();
        if (!o.quiet) Progress.getInstance(model).addProgressListener(new ProgressWriter(System.out));
        Solver<Lecture, Placement> solver = new Solver<Lecture, Placement>(properties);
        TimetableXMLLoader loader = new TimetableXMLLoader(model, assignment);
        loader.setInputFile(new File(o.input));
        loader.load();
        Solution<Lecture, Placement> solution = new Solution<Lecture, Placement>(model, assignment);
        solver.setInitalSolution(solution);
        if (model.getAllStudents().isEmpty()) {
            String msg = "instance " + o.input + " has NO STUDENTS (<students/> is empty): the student-conflict metric is undefined on it. "
                    + "In UniTime set the solver parameter 'Student Course Demands' (Curriculum.StudentCourseDemadsClass) to "
                    + "'Enrolled Student Course Demands', reload the solver and export again.";
            if (o.requireStudents) throw new IllegalStateException(msg);
            sLog.warn(msg);
            System.err.println("WARNING: " + msg);
        }

        RlRuntime runtime = RlRuntime.getOrCreate(model, cfg);
        runtime.attach(solver);
        ConflictReport initialReport = runtime.oracle.evaluate(assignment);
        SearchMetrics initial = SearchMetrics.compute(model, assignment, initialReport, cfg, runtime.scales, true, 0, 0);
        sLog.info("Initial: " + initialReport + " assigned=" + initial.assignedRatio);

        long t0 = System.nanoTime();
        solver.start();
        solver.getSolverThread().join();
        double wall = (System.nanoTime() - t0) / 1e9;

        RlNeighbourSelection rl = (solver.getNeighbourSelection() instanceof RlNeighbourSelection) ? (RlNeighbourSelection) solver.getNeighbourSelection() : null;
        Solution<Lecture, Placement> current = solver.lastSolution();
        long iterations = current.getIteration();
        // report the incumbent
        if (current.getBestInfo() != null) current.restoreBest();
        if (rl != null) rl.finish(current);
        ConflictReport finalReport = runtime.oracle.evaluate(current.getAssignment());
        SearchMetrics fin = SearchMetrics.compute(model, current.getAssignment(), finalReport, cfg, runtime.scales, true, iterations, current.getTime());

        Result r = new Result();
        r.initialMetrics = initial;
        r.finalMetrics = fin;
        Map<String, Object> m = r.metrics;
        m.put("arm", o.arm);
        m.put("input", o.input);
        m.put("seed", o.seed);
        m.put("wall_clock_sec", wall);
        m.put("solver_time_sec", current.getTime());
        m.put("iterations", iterations);
        m.put("committed", runtime.getCommitted());
        m.put("student_conflict_weight", properties.getPropertyDouble("Comparator.StudentConflictWeight", Double.NaN));
        m.put("comparator", properties.getProperty("Comparator.Class"));
        m.put("neighbour_class", properties.getProperty("Neighbour.Class"));
        m.put("initial", initial.toMap());
        m.put("final", fin.toMap());
        m.put("best_iteration", current.getBestIteration());
        m.put("best_time_sec", current.getBestTime());
        m.put("thresholds", runtime.thresholdReport());
        m.put("c_history", runtime.cHistory());
        m.put("scales", runtime.scales.toMap());
        if (rl != null) m.put("rl", rl.summary());
        Map<String, String> info = current.getInfo();
        m.put("solver_info", new LinkedHashMap<String, Object>(info));

        try (PrintWriter pw = new PrintWriter(new FileWriter(new File(outDir, "metrics.json")))) {
            pw.println(Json.write(m));
        }
        if (o.writeScales) {
            try (PrintWriter pw = new PrintWriter(new FileWriter(new File(outDir, "scales.properties")))) {
                pw.println("# normalisation scales frozen from " + o.arm + " on " + o.input);
                pw.println("Rl.Scale.O=" + fin.softPenalty);
                pw.println("Rl.Scale.Total=" + Math.abs(fin.totalValue));
                pw.println("Rl.Scale.Time=" + fin.timePref);
                pw.println("Rl.Scale.Room=" + fin.roomPref);
                pw.println("Rl.Scale.Dist=" + fin.distPref);
                pw.println("Rl.Scale.StudentConflict=" + fin.studentConflict);
                pw.println("Rl.Scale.TooBigRooms=" + fin.tooBigRooms);
                pw.println("Rl.Scale.UselessHalfHours=" + fin.uselessHalfHours);
                pw.println("Rl.Scale.BackToBack=" + fin.backToBack);
                pw.println("Rl.Scale.BrokenTimePatterns=" + fin.brokenTimePatterns);
            }
        }
        if (o.saveSolution) {
            TimetableXMLSaver saver = new TimetableXMLSaver(solver);
            saver.save(new File(outDir, "solution.xml"));
        }
        if (rl != null) rl.dispose();
        runtime.detach();
        RlRuntime.remove(model);
        sLog.info(String.format("Done: arm=%s seed=%d C=%.4f (checker %.4f) assigned=%.4f hard=%d soft=%.1f iters=%d committed=%d wall=%.1fs",
                o.arm, o.seed, fin.studentViolationRate(), fin.conflicts.checkerViolationRate(), fin.assignedRatio, fin.hardViolations,
                fin.softPenalty, iterations, runtime.getCommitted(), wall));
        System.out.println(Json.write(summaryLine(o, fin, wall, iterations, runtime.getCommitted())));
        return r;
    }

    private static Map<String, Object> summaryLine(Options o, SearchMetrics fin, double wall, long iterations, long committed) {
        Map<String, Object> s = new LinkedHashMap<String, Object>();
        s.put("arm", o.arm); s.put("seed", o.seed);
        s.put("C", fin.studentViolationRate()); s.put("C_checker", fin.conflicts.checkerViolationRate());
        s.put("students_total", fin.conflicts.studentsTotal);
        s.put("assigned_ratio", fin.assignedRatio); s.put("hard", fin.hardViolations); s.put("soft_penalty", fin.softPenalty);
        s.put("iterations", iterations); s.put("committed", committed); s.put("wall_clock_sec", wall);
        return s;
    }

    public static void main(String[] args) throws Exception {
        Options o = parse(args);
        run(o);
        System.exit(0);
    }
}
