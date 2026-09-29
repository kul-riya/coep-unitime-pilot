package org.unitime.timetable.solver.rl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.neighbourhoods.RoomChange;
import org.cpsolver.coursett.neighbourhoods.Suggestion;
import org.cpsolver.coursett.neighbourhoods.TimeChange;
import org.cpsolver.coursett.neighbourhoods.TimeSwap;
import org.cpsolver.coursett.sectioning.RandomStudentSwap;
import org.cpsolver.ifs.algorithms.neighbourhoods.RandomMove;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.heuristics.NeighbourSelection;
import org.cpsolver.ifs.model.Neighbour;
import org.cpsolver.ifs.util.DataProperties;

/**
 * The eight discrete actions. Operators 0-5 are stock CPSolver neighbourhoods; 6 and 7 are the same
 * generators with a conflict-biased variable sampler. Ids are frozen (they are the policy's output
 * indices and the one-hot in the state).
 */
public final class Operators {
    public static final int TIME_CHANGE = 0;
    public static final int ROOM_CHANGE = 1;
    public static final int TIME_AND_ROOM = 2;
    public static final int LECTURE_SWAP = 3;
    public static final int SUGGESTION = 4;
    public static final int STUDENT_SWAP = 5;
    public static final int BIASED_TIME_CHANGE = 6;
    public static final int BIASED_STUDENT_SWAP = 7;
    public static final int COUNT = 8;

    public static final String[] NAMES = {
        "TimeChange", "RoomChange", "RandomMove", "TimeSwap", "Suggestion", "RandomStudentSwap",
        "ConflictBiasedTimeMove", "ConflictBiasedStudentSwap"
    };

    private Operators() {}

    /** Instantiate all delegates. They still need {@code init(solver)}. */
    public static List<NeighbourSelection<Lecture, Placement>> create(DataProperties config, RlRuntime runtime) throws Exception {
        List<NeighbourSelection<Lecture, Placement>> ops = new ArrayList<NeighbourSelection<Lecture, Placement>>(COUNT);
        ops.add(new TimeChange(config));
        ops.add(new RoomChange(config));
        ops.add(new RandomMove<Lecture, Placement>(config));
        ops.add(new TimeSwap(config));
        ops.add(new Suggestion(config));
        ops.add(new RandomStudentSwap(config));
        ops.add(new ConflictBiasedTimeMove(config, runtime));
        ops.add(new ConflictBiasedStudentSwap(config, runtime));
        return ops;
    }

    public static boolean isStudentOperator(int id) {
        return id == STUDENT_SWAP || id == BIASED_STUDENT_SWAP;
    }

    /**
     * Neighbour that changes nothing. Returned when every operator is masked for the rest of a
     * macro-step, so the Great Deluge loop terminates and the solver still counts the iteration.
     */
    public static final class NoOpNeighbour implements Neighbour<Lecture, Placement> {
        public static final NoOpNeighbour INSTANCE = new NoOpNeighbour();
        @Override public void assign(Assignment<Lecture, Placement> assignment, long iteration) {}
        @Override public double value(Assignment<Lecture, Placement> assignment) { return 0.0; }
        @Override public Map<Lecture, Placement> assignments() { return Collections.emptyMap(); }
        @Override public String toString() { return "NoOp"; }
    }
}
