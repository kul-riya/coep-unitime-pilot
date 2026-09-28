package org.unitime.timetable.solver.rl;

import java.util.Collections;
import java.util.Map;
import java.util.Set;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Student;

/**
 * Immutable snapshot of the student-conflict checker.
 *
 * Conflict definition (mirrors scripts/eval_timetable_kpis.py): a student is conflicted when two of
 * that student's assigned classes have a pairwise time intersection. Pairs flagged by
 * {@link Lecture#isToIgnoreStudentConflictsWith(Lecture)} are skipped, as UniTime does.
 */
public final class ConflictReport {
    public static final int SLOT_BINS = 10;

    /** students with at least two assigned classes */
    public final int studentsWithTwoPlus;
    /** all students in the model */
    public final int studentsTotal;
    /** students with at least one pairwise overlap */
    public final int conflictedStudents;
    /** total (student, pair) violations */
    public final long violatedStudentPairs;
    /** joint-enrollment constraints with jenrl &gt; 0 */
    public final int pairsTotal;
    /** of those, both assigned and overlapping */
    public final int pairsViolated;
    /** mean number of distinct conflicting partner classes per conflicted student */
    public final double intensity;
    /** share of violated (student, pair) incidences that involve the worst 10% of classes */
    public final double concentration;
    /** conflict counts per day-period bin, each divided by the bin maximum */
    public final double[] slotProfile;
    /** per-class violated-incidence counts (student-weighted); missing = 0 */
    public final Map<Lecture, Double> classScores;
    /** the conflicted students */
    public final Set<Student> conflicted;
    /** number of lectures that participate in at least one violation */
    public final int lecturesInConflict;

    ConflictReport(int studentsWithTwoPlus, int studentsTotal, int conflictedStudents, long violatedStudentPairs,
            int pairsTotal, int pairsViolated, double intensity, double concentration, double[] slotProfile,
            Map<Lecture, Double> classScores, Set<Student> conflicted, int lecturesInConflict) {
        this.studentsWithTwoPlus = studentsWithTwoPlus;
        this.studentsTotal = studentsTotal;
        this.conflictedStudents = conflictedStudents;
        this.violatedStudentPairs = violatedStudentPairs;
        this.pairsTotal = pairsTotal;
        this.pairsViolated = pairsViolated;
        this.intensity = intensity;
        this.concentration = concentration;
        this.slotProfile = slotProfile;
        this.classScores = Collections.unmodifiableMap(classScores);
        this.conflicted = Collections.unmodifiableSet(conflicted);
        this.lecturesInConflict = lecturesInConflict;
    }

    /** C in the research document: conflicted students over students with two or more assigned classes. */
    public double studentViolationRate() {
        return studentsWithTwoPlus == 0 ? 0.0 : (double) conflictedStudents / studentsWithTwoPlus;
    }

    /** The KPI script's denominator: all students. */
    public double checkerViolationRate() {
        return studentsTotal == 0 ? 0.0 : (double) conflictedStudents / studentsTotal;
    }

    public double pairViolationRate() {
        return pairsTotal == 0 ? 0.0 : (double) pairsViolated / pairsTotal;
    }

    public double zeroConflictFraction() {
        return studentsTotal == 0 ? 1.0 : 1.0 - (double) conflictedStudents / studentsTotal;
    }

    @Override
    public String toString() {
        return String.format("C=%.4f (%d/%d) checker=%.4f pairs=%d/%d intensity=%.2f conc=%.2f",
                studentViolationRate(), conflictedStudents, studentsWithTwoPlus, checkerViolationRate(),
                pairsViolated, pairsTotal, intensity, concentration);
    }
}
