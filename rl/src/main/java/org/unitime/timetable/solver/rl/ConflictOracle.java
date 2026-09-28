package org.unitime.timetable.solver.rl;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.cpsolver.coursett.Constants;
import org.cpsolver.coursett.constraint.JenrlConstraint;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.Student;
import org.cpsolver.coursett.model.TimeLocation;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;

/**
 * Student-conflict checker over a {@link TimetableModel}, with an incremental path.
 *
 * {@link #evaluate(Assignment)} recomputes everything. {@link #update(Assignment, Collection, boolean)}
 * recomputes only the students of the given lectures (or everything when sectioning changed) and keeps
 * aggregate counters consistent. Both return a {@link ConflictReport}; {@link #last()} returns the most
 * recent one without recomputation.
 */
public class ConflictOracle {
    private final TimetableModel iModel;
    private final int iFirstDaySlot, iLastDaySlot;

    // per-student cached state
    private final Map<Student, StudentState> iStates = new HashMap<Student, StudentState>();
    // aggregates
    private int iStudentsWithTwoPlus = 0;
    private int iConflictedStudents = 0;
    private long iViolatedStudentPairs = 0;
    private final Map<Lecture, Double> iClassScores = new HashMap<Lecture, Double>();
    private final long[] iSlotBins = new long[ConflictReport.SLOT_BINS];
    private final Set<Student> iConflicted = new HashSet<Student>();
    // jenrl pair state
    private final Set<JenrlConstraint> iViolatedPairs = new HashSet<JenrlConstraint>();
    private ConflictReport iLast = null;
    private long iFullRecomputes = 0, iIncrementalUpdates = 0;

    private static final class StudentState {
        int assigned;
        boolean conflicted;
        int pairs;
        Set<Lecture> partners = Collections.emptySet();
        Map<Lecture, Integer> classIncidence = Collections.emptyMap();
        int[] bins = null;
    }

    public ConflictOracle(TimetableModel model) {
        iModel = model;
        iFirstDaySlot = model.getProperties().getPropertyInt("General.FirstDaySlot", Constants.DAY_SLOTS_FIRST);
        iLastDaySlot = model.getProperties().getPropertyInt("General.LastDaySlot", Constants.DAY_SLOTS_LAST);
    }

    public TimetableModel getModel() { return iModel; }
    public long getFullRecomputes() { return iFullRecomputes; }
    public long getIncrementalUpdates() { return iIncrementalUpdates; }

    /** Two lectures conflict for a student iff both assigned and their times intersect (checker definition). */
    public static boolean conflicts(Lecture l1, Placement p1, Lecture l2, Placement p2) {
        if (p1 == null || p2 == null) return false;
        if (l1.isToIgnoreStudentConflictsWith(l2)) return false;
        return p1.getTimeLocation().hasIntersection(p2.getTimeLocation());
    }

    /** Full recompute. */
    public synchronized ConflictReport evaluate(Assignment<Lecture, Placement> assignment) {
        iStates.clear();
        iStudentsWithTwoPlus = 0;
        iConflictedStudents = 0;
        iViolatedStudentPairs = 0;
        iClassScores.clear();
        java.util.Arrays.fill(iSlotBins, 0L);
        iConflicted.clear();
        for (Student student: iModel.getAllStudents())
            add(student, compute(student, assignment));
        iViolatedPairs.clear();
        for (JenrlConstraint jenrl: iModel.getJenrlConstraints())
            if (pairViolated(jenrl, assignment)) iViolatedPairs.add(jenrl);
        iFullRecomputes++;
        return iLast = report();
    }

    /**
     * Incremental update.
     * @param touched lectures whose placement changed since the last call
     * @param sectioningChanged true when students moved between sections (forces a full recompute)
     */
    public synchronized ConflictReport update(Assignment<Lecture, Placement> assignment, Collection<Lecture> touched, boolean sectioningChanged) {
        if (iLast == null || sectioningChanged) return evaluate(assignment);
        if (touched.isEmpty()) return iLast;
        Set<Student> students = new HashSet<Student>();
        Set<JenrlConstraint> jenrls = new HashSet<JenrlConstraint>();
        for (Lecture lecture: touched) {
            students.addAll(lecture.students());
            jenrls.addAll(lecture.jenrlConstraints());
        }
        for (Student student: students) {
            StudentState old = iStates.get(student);
            if (old != null) remove(student, old);
            add(student, compute(student, assignment));
        }
        for (JenrlConstraint jenrl: jenrls) {
            if (pairViolated(jenrl, assignment)) iViolatedPairs.add(jenrl); else iViolatedPairs.remove(jenrl);
        }
        iIncrementalUpdates++;
        return iLast = report();
    }

    /** Most recent report (full recompute if none yet). */
    public synchronized ConflictReport last(Assignment<Lecture, Placement> assignment) {
        return iLast == null ? evaluate(assignment) : iLast;
    }

    /** Compare the incremental state against a fresh recompute; returns the absolute difference in C. */
    public synchronized double driftCheck(Assignment<Lecture, Placement> assignment) {
        ConflictReport before = iLast;
        ConflictReport after = evaluate(assignment);
        if (before == null) return 0.0;
        return Math.abs(before.studentViolationRate() - after.studentViolationRate())
                + Math.abs(before.conflictedStudents - after.conflictedStudents)
                + Math.abs(before.pairsViolated - after.pairsViolated);
    }

    private boolean pairViolated(JenrlConstraint jenrl, Assignment<Lecture, Placement> assignment) {
        if (jenrl.getJenrl() <= 0) return false;
        Lecture l1 = jenrl.first(), l2 = jenrl.second();
        return conflicts(l1, assignment.getValue(l1), l2, assignment.getValue(l2));
    }

    private StudentState compute(Student student, Assignment<Lecture, Placement> assignment) {
        StudentState s = new StudentState();
        List<Lecture> lectures = new ArrayList<Lecture>();
        List<Placement> placements = new ArrayList<Placement>();
        for (Lecture lecture: student.getLectures()) {
            Placement p = assignment.getValue(lecture);
            if (p == null) continue;
            lectures.add(lecture);
            placements.add(p);
        }
        s.assigned = lectures.size();
        if (s.assigned < 2) return s;
        Set<Lecture> partners = null;
        Map<Lecture, Integer> incidence = null;
        for (int i = 0; i < lectures.size(); i++) {
            for (int j = i + 1; j < lectures.size(); j++) {
                if (!conflicts(lectures.get(i), placements.get(i), lectures.get(j), placements.get(j))) continue;
                if (partners == null) {
                    partners = new HashSet<Lecture>();
                    incidence = new HashMap<Lecture, Integer>();
                    s.bins = new int[ConflictReport.SLOT_BINS];
                }
                s.pairs++;
                partners.add(lectures.get(i));
                partners.add(lectures.get(j));
                incidence.merge(lectures.get(i), 1, Integer::sum);
                incidence.merge(lectures.get(j), 1, Integer::sum);
                s.bins[bin(placements.get(i).getTimeLocation(), placements.get(j).getTimeLocation())]++;
            }
        }
        if (partners != null) {
            s.conflicted = true;
            s.partners = partners;
            s.classIncidence = incidence;
        }
        return s;
    }

    private int bin(TimeLocation t1, TimeLocation t2) {
        int start = Math.max(t1.getStartSlot(), t2.getStartSlot());
        int span = Math.max(1, iLastDaySlot - iFirstDaySlot + 1);
        int b = (int) ((long) (start - iFirstDaySlot) * ConflictReport.SLOT_BINS / span);
        return Math.max(0, Math.min(ConflictReport.SLOT_BINS - 1, b));
    }

    private void add(Student student, StudentState s) {
        iStates.put(student, s);
        if (s.assigned >= 2) iStudentsWithTwoPlus++;
        if (s.conflicted) {
            iConflictedStudents++;
            iConflicted.add(student);
            iViolatedStudentPairs += s.pairs;
            for (Map.Entry<Lecture, Integer> e: s.classIncidence.entrySet())
                iClassScores.merge(e.getKey(), (double) e.getValue(), Double::sum);
            for (int b = 0; b < ConflictReport.SLOT_BINS; b++) iSlotBins[b] += s.bins[b];
        }
    }

    private void remove(Student student, StudentState s) {
        if (s.assigned >= 2) iStudentsWithTwoPlus--;
        if (s.conflicted) {
            iConflictedStudents--;
            iConflicted.remove(student);
            iViolatedStudentPairs -= s.pairs;
            for (Map.Entry<Lecture, Integer> e: s.classIncidence.entrySet()) {
                Double v = iClassScores.get(e.getKey());
                if (v == null) continue;
                double nv = v - e.getValue();
                if (nv <= 1e-9) iClassScores.remove(e.getKey()); else iClassScores.put(e.getKey(), nv);
            }
            for (int b = 0; b < ConflictReport.SLOT_BINS; b++) iSlotBins[b] -= s.bins[b];
        }
    }

    private ConflictReport report() {
        double intensity = 0.0;
        if (iConflictedStudents > 0) {
            long partners = 0;
            for (Student st: iConflicted) partners += iStates.get(st).partners.size();
            intensity = (double) partners / iConflictedStudents;
        }
        double concentration = 0.0;
        if (!iClassScores.isEmpty()) {
            List<Double> scores = new ArrayList<Double>(iClassScores.values());
            Collections.sort(scores, Collections.reverseOrder());
            int nClasses = iModel.variables().size();
            int top = Math.max(1, (int) Math.ceil(0.10 * nClasses));
            double sum = 0, topSum = 0;
            for (int i = 0; i < scores.size(); i++) {
                sum += scores.get(i);
                if (i < top) topSum += scores.get(i);
            }
            concentration = sum > 0 ? topSum / sum : 0.0;
        }
        double[] profile = new double[ConflictReport.SLOT_BINS];
        long max = 0;
        for (long b: iSlotBins) max = Math.max(max, b);
        if (max > 0) for (int b = 0; b < profile.length; b++) profile[b] = (double) iSlotBins[b] / max;
        int pairsTotal = 0;
        for (JenrlConstraint j: iModel.getJenrlConstraints()) if (j.getJenrl() > 0) pairsTotal++;
        return new ConflictReport(iStudentsWithTwoPlus, iModel.getAllStudents().size(), iConflictedStudents,
                iViolatedStudentPairs, pairsTotal, iViolatedPairs.size(), intensity, concentration, profile,
                new HashMap<Lecture, Double>(iClassScores), new HashSet<Student>(iConflicted), iClassScores.size());
    }
}
