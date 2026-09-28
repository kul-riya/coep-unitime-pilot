package org.unitime.timetable.solver.rl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.cpsolver.coursett.TimetableXMLLoader;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.assignment.DefaultSingleAssignment;
import org.cpsolver.ifs.util.DataProperties;
import org.cpsolver.ifs.util.ToolBox;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** The incremental checker must agree with a full recompute after arbitrary sequences of moves. */
public class ConflictOracleTest {
    static TimetableModel model;
    static Assignment<Lecture, Placement> assignment;

    @BeforeAll
    static void load() throws Exception {
        File dir = Files.createTempDirectory("rl-oracle").toFile();
        File xml = new File(dir, "inst.xml");
        Map<String, Integer> o = new LinkedHashMap<String, Integer>();
        o.put("classes", 40); o.put("students", 200); o.put("rooms", 4); o.put("seed", 3);
        o.put("domain", 5); o.put("band", 8); o.put("take", 6); o.put("sections", 2); o.put("coursesPerBlock", 8);
        SyntheticInstance.build(xml, o);
        DataProperties p = new DataProperties();
        p.setProperty("General.Input", xml.getPath());
        model = new TimetableModel(p);
        assignment = new DefaultSingleAssignment<Lecture, Placement>();
        TimetableXMLLoader loader = new TimetableXMLLoader(model, assignment);
        loader.setInputFile(xml);
        loader.load();
        ToolBox.setSeed(11);
    }

    private static void randomMove(Random rnd, List<Lecture> touched) {
        Lecture lecture = model.variables().get(rnd.nextInt(model.variables().size()));
        List<Placement> values = lecture.values(assignment);
        if (values.isEmpty()) return;
        if (assignment.getValue(lecture) != null && rnd.nextInt(5) == 0) {
            assignment.unassign(0, lecture);
            touched.add(lecture);
            return;
        }
        Placement placement = values.get(rnd.nextInt(values.size()));
        for (Placement conflict: new ArrayList<Placement>(model.conflictValues(assignment, placement))) {
            assignment.unassign(0, conflict.variable());
            touched.add(conflict.variable());
        }
        assignment.assign(0, placement);
        touched.add(lecture);
    }

    private static void assertSame(ConflictReport a, ConflictReport b) {
        assertEquals(a.conflictedStudents, b.conflictedStudents, "conflicted students");
        assertEquals(a.studentsWithTwoPlus, b.studentsWithTwoPlus, "students with 2+ classes");
        assertEquals(a.violatedStudentPairs, b.violatedStudentPairs, "violated (student, pair)");
        assertEquals(a.pairsViolated, b.pairsViolated, "violated jenrl pairs");
        assertEquals(a.pairsTotal, b.pairsTotal, "jenrl pairs");
        assertEquals(a.intensity, b.intensity, 1e-9, "intensity");
        assertEquals(a.concentration, b.concentration, 1e-9, "concentration");
        assertEquals(a.classScores.size(), b.classScores.size(), "classes in conflict");
        for (int i = 0; i < ConflictReport.SLOT_BINS; i++) assertEquals(a.slotProfile[i], b.slotProfile[i], 1e-9, "slot bin " + i);
    }

    @Test
    void incrementalMatchesFullRecompute() {
        ConflictOracle inc = new ConflictOracle(model);
        ConflictOracle full = new ConflictOracle(model);
        Random rnd = new Random(5);
        List<Lecture> touched = new ArrayList<Lecture>();
        for (int i = 0; i < 300; i++) randomMove(rnd, touched);
        assertSame(full.evaluate(assignment), inc.evaluate(assignment));
        int rounds = 0;
        for (int round = 0; round < 200; round++) {
            touched.clear();
            int moves = 1 + rnd.nextInt(4);
            for (int m = 0; m < moves; m++) randomMove(rnd, touched);
            ConflictReport a = inc.update(assignment, touched, false);
            ConflictReport b = full.evaluate(assignment);
            assertSame(b, a);
            rounds++;
        }
        assertTrue(rounds == 200);
        assertTrue(inc.getIncrementalUpdates() >= 100, "incremental path was used");
        assertEquals(0.0, inc.driftCheck(assignment), 1e-12);
    }

    @Test
    void ratesAreConsistent() {
        ConflictOracle oracle = new ConflictOracle(model);
        ConflictReport r = oracle.evaluate(assignment);
        assertTrue(r.studentViolationRate() >= 0 && r.studentViolationRate() <= 1);
        assertTrue(r.checkerViolationRate() <= r.studentViolationRate() + 1e-12);
        assertEquals(1.0 - (double) r.conflictedStudents / r.studentsTotal, r.zeroConflictFraction(), 1e-12);
    }

    @Test
    void stateVectorHasFixedDimension() {
        RlConfig cfg = new RlConfig(new DataProperties());
        SearchMetrics.Scales scales = new SearchMetrics.Scales(cfg);
        ConflictOracle oracle = new ConflictOracle(model);
        SearchMetrics m = SearchMetrics.compute(model, assignment, oracle.evaluate(assignment), cfg, scales, true, 0, 0);
        float[] x = StateEncoder.encode(m, scales, new StateEncoder.Dynamics(), cfg);
        assertEquals(StateEncoder.DIM, x.length);
        assertEquals(StateEncoder.DIM, StateEncoder.NAMES.length);
        for (float v: x) assertTrue(Float.isFinite(v));
    }
}
