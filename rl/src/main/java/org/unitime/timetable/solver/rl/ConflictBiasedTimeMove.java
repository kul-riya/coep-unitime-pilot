package org.unitime.timetable.solver.rl;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.RoomLocation;
import org.cpsolver.coursett.model.TimeLocation;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.coursett.neighbourhoods.TimeChange;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.model.Neighbour;
import org.cpsolver.ifs.model.SimpleNeighbour;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.util.DataProperties;
import org.cpsolver.ifs.util.ToolBox;

/**
 * Operator 6: {@link TimeChange} whose lecture is sampled proportionally to the conflict checker's
 * per-class conflict score instead of uniformly. Falls back to the uniform operator when there are
 * no conflicts or no valid move was found for the sampled lectures.
 */
public class ConflictBiasedTimeMove extends TimeChange {
    private final RlRuntime iRuntime;
    private final int iAttempts;
    private ConflictReport iCachedReport = null;
    private Lecture[] iLectures = null;
    private double[] iCumulative = null;

    public ConflictBiasedTimeMove(DataProperties config, RlRuntime runtime) {
        super(config);
        iRuntime = runtime;
        iAttempts = config.getPropertyInt("Rl.Biased.Attempts", 5);
    }

    private void refresh(ConflictReport report) {
        if (report == iCachedReport) return;
        iCachedReport = report;
        List<Lecture> lectures = new ArrayList<Lecture>(report.classScores.size());
        List<Double> weights = new ArrayList<Double>(report.classScores.size());
        for (Map.Entry<Lecture, Double> e: report.classScores.entrySet()) {
            lectures.add(e.getKey());
            weights.add(e.getValue());
        }
        iLectures = lectures.toArray(new Lecture[0]);
        iCumulative = new double[iLectures.length];
        double total = 0;
        for (int i = 0; i < iLectures.length; i++) {
            total += weights.get(i);
            iCumulative[i] = total;
        }
    }

    private Lecture sample() {
        if (iLectures == null || iLectures.length == 0) return null;
        double total = iCumulative[iCumulative.length - 1];
        if (total <= 0) return iLectures[ToolBox.random(iLectures.length)];
        double u = ToolBox.random() * total;
        int lo = 0, hi = iCumulative.length - 1;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (iCumulative[mid] >= u) hi = mid; else lo = mid + 1;
        }
        return iLectures[lo];
    }

    @Override
    public Neighbour<Lecture, Placement> selectNeighbour(Solution<Lecture, Placement> solution) {
        TimetableModel model = (TimetableModel) solution.getModel();
        Assignment<Lecture, Placement> assignment = solution.getAssignment();
        refresh(iRuntime.oracle.last(assignment));
        for (int attempt = 0; attempt < iAttempts; attempt++) {
            Lecture lecture = sample();
            if (lecture == null) break;
            Neighbour<Lecture, Placement> n = timeMove(model, assignment, lecture);
            if (n != null) return n;
        }
        return super.selectNeighbour(solution);
    }

    /** Same move construction as {@link TimeChange#selectNeighbour}, for one given lecture. */
    private Neighbour<Lecture, Placement> timeMove(TimetableModel model, Assignment<Lecture, Placement> assignment, Lecture lecture) {
        Placement old = assignment.getValue(lecture);
        if (old == null) return null;
        List<TimeLocation> values = lecture.timeLocations();
        if (values.isEmpty()) return null;
        int valIdx = ToolBox.random(values.size());
        for (int j = 0; j < values.size(); j++) {
            TimeLocation time = values.get((j + valIdx) % values.size());
            if (time.getPreference() > 50) continue;
            if (time.equals(old.getTimeLocation())) continue;
            Placement placement;
            if (lecture.getNrRooms() == 0)
                placement = new Placement(lecture, time, (RoomLocation) null);
            else if (lecture.getNrRooms() == 1)
                placement = new Placement(lecture, time, old.getRoomLocation());
            else
                placement = new Placement(lecture, time, old.getRoomLocations());
            if (placement.isValid() && !model.inConflict(assignment, placement)) {
                SimpleNeighbour<Lecture, Placement> n = new SimpleNeighbour<Lecture, Placement>(lecture, placement);
                if (!iHC || n.value(assignment) <= 0) return n;
            }
        }
        return null;
    }
}
