package org.unitime.timetable.solver.rl;

import java.util.Map;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.sectioning.StudentMove;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.model.Neighbour;

/**
 * Maps a neighbour produced by the default selector onto the operator id that would have proposed
 * it. Used in shadow mode to build behaviour-cloning targets and the disagreement rate. Must be
 * called before the neighbour is assigned (the assignment still holds the old placements).
 */
public final class OperatorLabeler {
    private OperatorLabeler() {}

    /** @return operator id, or -1 when the neighbour is null / a no-op */
    public static int label(Neighbour<Lecture, Placement> n, Assignment<Lecture, Placement> assignment) {
        if (n == null || n instanceof Operators.NoOpNeighbour) return -1;
        if (n instanceof StudentMove) return Operators.STUDENT_SWAP;
        String cls = n.getClass().getName();
        if (cls.contains("Suggestion")) return Operators.SUGGESTION;
        Map<Lecture, Placement> moves = n.assignments();
        if (moves == null || moves.isEmpty()) return Operators.SUGGESTION;
        if (moves.size() == 1) {
            Map.Entry<Lecture, Placement> e = moves.entrySet().iterator().next();
            Placement old = assignment.getValue(e.getKey());
            Placement neu = e.getValue();
            if (old == null || neu == null) return Operators.TIME_AND_ROOM;
            boolean sameTime = old.getTimeLocation().equals(neu.getTimeLocation());
            boolean sameRooms = old.sameRooms(neu);
            if (!sameTime && sameRooms) return Operators.TIME_CHANGE;
            if (sameTime && !sameRooms) return Operators.ROOM_CHANGE;
            return Operators.TIME_AND_ROOM;
        }
        if (moves.size() == 2) {
            // an exchange: each lecture takes (roughly) the other's old time
            Lecture[] ls = moves.keySet().toArray(new Lecture[0]);
            Placement o0 = assignment.getValue(ls[0]), o1 = assignment.getValue(ls[1]);
            Placement n0 = moves.get(ls[0]), n1 = moves.get(ls[1]);
            if (o0 != null && o1 != null && n0 != null && n1 != null
                    && n0.getTimeLocation().equals(o1.getTimeLocation()) && n1.getTimeLocation().equals(o0.getTimeLocation()))
                return Operators.LECTURE_SWAP;
        }
        return Operators.SUGGESTION;
    }
}
