package org.unitime.timetable.solver.rl;

import java.util.ArrayList;
import java.util.List;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.Student;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.coursett.sectioning.StudentSwapGenerator;
import org.cpsolver.ifs.algorithms.neighbourhoods.HillClimberSelection;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.model.Neighbour;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.util.DataProperties;
import org.cpsolver.ifs.util.ToolBox;

/**
 * Operator 7: {@link org.cpsolver.coursett.sectioning.RandomStudentSwap} with the student drawn from
 * the conflict checker's conflicted-student set, and the offering drawn from that student's
 * conflicting classes.
 */
public class ConflictBiasedStudentSwap extends StudentSwapGenerator implements HillClimberSelection {
    private final RlRuntime iRuntime;
    private final int iAttempts;
    private boolean iHC = false;
    private boolean iEnabled = true;
    private ConflictReport iCachedReport = null;
    private Student[] iConflicted = null;

    public ConflictBiasedStudentSwap(DataProperties config, RlRuntime runtime) {
        super();
        iRuntime = runtime;
        iAttempts = config.getPropertyInt("Rl.Biased.Attempts", 5);
    }

    @Override
    public void init(Solver<Lecture, Placement> solver) {
        super.init(solver);
        iEnabled = solver.hasSingleSolution();
    }

    @Override
    public void setHcMode(boolean hcMode) { iHC = hcMode; }

    private void refresh(ConflictReport report) {
        if (report == iCachedReport) return;
        iCachedReport = report;
        iConflicted = report.conflicted.toArray(new Student[0]);
    }

    @Override
    public Neighbour<Lecture, Placement> selectNeighbour(Solution<Lecture, Placement> solution) {
        if (!iEnabled) return null;
        TimetableModel model = (TimetableModel) solution.getModel();
        if (model.getAllStudents().isEmpty()) return null;
        if (!model.isOnFlySectioningEnabled()) model.setOnFlySectioningEnabled(true);
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        refresh(iRuntime.oracle.last(assignment));
        if (iConflicted == null || iConflicted.length == 0) return null;
        for (int attempt = 0; attempt < iAttempts; attempt++) {
            Student student = iConflicted[ToolBox.random(iConflicted.length)];
            List<Lecture> inConflict = conflictingLectures(student, assignment);
            if (inConflict.isEmpty()) continue;
            int start = ToolBox.random(inConflict.size());
            for (int i = 0; i < inConflict.size(); i++) {
                Lecture lecture = inConflict.get((start + i) % inConflict.size());
                if (lecture.getConfiguration() == null) continue;
                Neighbour<Lecture, Placement> n = generateSwap(model, assignment, student, lecture.getConfiguration());
                if (n != null && (!iHC || n.value(assignment) <= 0.0)) return n;
            }
        }
        return null;
    }

    private static List<Lecture> conflictingLectures(Student student, Assignment<Lecture, Placement> assignment) {
        List<Lecture> lectures = new ArrayList<Lecture>(student.getLectures());
        List<Lecture> result = new ArrayList<Lecture>();
        for (int i = 0; i < lectures.size(); i++) {
            Lecture l1 = lectures.get(i);
            Placement p1 = assignment.getValue(l1);
            if (p1 == null) continue;
            for (int j = 0; j < lectures.size(); j++) {
                if (i == j) continue;
                Lecture l2 = lectures.get(j);
                if (ConflictOracle.conflicts(l1, p1, l2, assignment.getValue(l2))) { result.add(l1); break; }
            }
        }
        return result;
    }
}
