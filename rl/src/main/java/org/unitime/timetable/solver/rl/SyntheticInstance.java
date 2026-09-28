package org.unitime.timetable.solver.rl;

import java.io.File;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.cpsolver.coursett.TimetableXMLSaver;
import org.cpsolver.coursett.constraint.InstructorConstraint;
import org.cpsolver.coursett.constraint.JenrlConstraint;
import org.cpsolver.coursett.constraint.RoomConstraint;
import org.cpsolver.coursett.model.Configuration;
import org.cpsolver.coursett.model.Lecture;
import org.cpsolver.coursett.model.Placement;
import org.cpsolver.coursett.model.RoomLocation;
import org.cpsolver.coursett.model.Student;
import org.cpsolver.coursett.model.TimeLocation;
import org.cpsolver.coursett.model.TimetableModel;
import org.cpsolver.ifs.assignment.Assignment;
import org.cpsolver.ifs.assignment.DefaultSingleAssignment;
import org.cpsolver.ifs.solution.Solution;
import org.cpsolver.ifs.solver.Solver;
import org.cpsolver.ifs.util.DataProperties;

/**
 * COEP-shaped synthetic instance for smoke tests and throughput measurement.
 *
 * A 5-day week of 60-minute slots from 8:30 to 18:30 with a 12:30 lunch hole. Students are grouped
 * in cohorts (a "class" in Taasika terms); a cohort takes {@code take} of the {@code coursesPerBlock}
 * courses of its block, so cohort members share almost all their lectures. Every lecture of a block
 * may only meet inside a {@code band}-hour window of the week and each lecture sees only
 * {@code domain} of those hours, so overlaps are unavoidable when take &gt; band and only partly
 * reducible otherwise: the regime the research question is about. Writes a CPSolver timetable XML
 * that {@link HeadlessSolve} and {@link EnvServer} can load; warm-start it with a stock solve and
 * --save-solution to obtain an instance with an initial solution, as a UniTime export would have.
 *
 * <pre>
 * java -cp unitime-rl-all.jar org.unitime.timetable.solver.rl.SyntheticInstance out.xml \
 *      classes=120 students=600 rooms=6 seed=7 domain=4 band=8 take=6 sections=1 coursesPerBlock=10
 * </pre>
 */
public class SyntheticInstance {
    public static void main(String[] args) throws Exception {
        File out = new File(args.length > 0 ? args[0] : "rl/instances/synthetic.xml");
        Map<String, Integer> o = new LinkedHashMap<String, Integer>();
        o.put("classes", 120); o.put("students", 600); o.put("rooms", 6); o.put("seed", 7);
        o.put("domain", 0); o.put("band", 0); o.put("take", 6); o.put("sections", 1); o.put("coursesPerBlock", 10);
        for (int i = 1; i < args.length; i++) {
            String[] kv = args[i].split("=", 2);
            if (kv.length != 2 || !o.containsKey(kv[0])) throw new IllegalArgumentException("unknown parameter " + args[i] + "; known: " + o.keySet());
            o.put(kv[0], Integer.valueOf(kv[1]));
        }
        build(out, o);
        System.out.println("wrote " + out + " " + o);
    }

    public static void build(File out, Map<String, Integer> o) throws Exception {
        int nrClasses = o.get("classes"), nrStudents = o.get("students"), nrRooms = o.get("rooms");
        int domain = o.get("domain"), band = o.get("band"), take = o.get("take"), sectionsPerCourse = Math.max(1, o.get("sections"));
        int coursesPerBlock = Math.max(1, o.get("coursesPerBlock"));
        Random rnd = new Random(o.get("seed"));
        DataProperties p = new DataProperties();
        p.setProperty("General.Output", out.getParent() == null ? "." : out.getParent());
        p.setProperty("Xml.ShowNames", "true");
        p.setProperty("Xml.ExportStudentSectioning", "true");
        p.setProperty("Xml.SaveBest", "false");
        p.setProperty("Xml.SaveInitial", "false");
        p.setProperty("Xml.SaveCurrent", "true");
        p.setProperty("General.FirstDaySlot", String.valueOf((8 * 60 + 30) / 5));
        p.setProperty("General.LastDaySlot", String.valueOf((18 * 60 + 30) / 5 - 1));
        p.setProperty("General.LastWorkDay", "4");
        TimetableModel model = new TimetableModel(p);
        Assignment<Lecture, Placement> assignment = new DefaultSingleAssignment<Lecture, Placement>();

        List<RoomConstraint> rooms = new ArrayList<RoomConstraint>();
        for (int r = 0; r < nrRooms; r++) {
            int capacity = 60 + 30 * (r % 3);
            RoomConstraint rc = new RoomConstraint(Long.valueOf(1000 + r), "R" + r, Long.valueOf(1), capacity, null, 0.0, 0.0, false, true);
            model.addConstraint(rc);
            rooms.add(rc);
        }
        List<InstructorConstraint> instructors = new ArrayList<InstructorConstraint>();
        for (int i = 0; i < Math.max(1, nrClasses / 3); i++) {
            InstructorConstraint ic = new InstructorConstraint(Long.valueOf(2000 + i), "I" + i, "Instructor " + i, false);
            model.addConstraint(ic);
            instructors.add(ic);
        }
        BitSet weeks = new BitSet();
        weeks.set(0, 14);
        int firstSlot = (8 * 60 + 30) / 5;
        List<int[]> hours = new ArrayList<int[]>(); // {dayCode, startSlot}, ordered by day then hour
        for (int day = 0; day < 5; day++) {
            int dayCode = 1 << (6 - day);
            for (int h = 0; h < 10; h++) {
                int start = firstSlot + 12 * h;
                if (start == (12 * 60 + 30) / 5) continue;
                hours.add(new int[] {dayCode, start});
            }
        }

        int nrCourses = Math.max(1, nrClasses / sectionsPerCourse);
        int nrBlocks = Math.max(1, nrCourses / coursesPerBlock);
        List<Lecture> lectures = new ArrayList<Lecture>();
        List<Configuration> configs = new ArrayList<Configuration>();
        Map<Integer, List<Lecture>> sectionsOf = new HashMap<Integer, List<Lecture>>();
        // one time band per block
        int[] bandStart = new int[nrBlocks];
        for (int b = 0; b < nrBlocks; b++)
            bandStart[b] = (band > 0 && band < hours.size()) ? rnd.nextInt(hours.size() - band + 1) : 0;
        long classId = 1;
        for (int c = 0; c < nrCourses; c++) {
            int block = Math.min(nrBlocks - 1, c / coursesPerBlock);
            Configuration config = new Configuration(Long.valueOf(100 + c), Long.valueOf(200 + c), -1);
            configs.add(config);
            List<Lecture> sections = new ArrayList<Lecture>();
            for (int s = 0; s < sectionsPerCourse && lectures.size() < nrClasses; s++) {
                int limit = 40 + rnd.nextInt(40);
                List<int[]> candidates;
                if (band > 0 && band < hours.size()) candidates = new ArrayList<int[]>(hours.subList(bandStart[block], bandStart[block] + band));
                else candidates = new ArrayList<int[]>(hours);
                if (domain > 0 && domain < candidates.size()) {
                    int start = rnd.nextInt(candidates.size() - domain + 1);
                    candidates = new ArrayList<int[]>(candidates.subList(start, start + domain));
                }
                List<TimeLocation> times = new ArrayList<TimeLocation>();
                for (int[] h: candidates) {
                    int pref = (h[1] >= (16 * 60 + 30) / 5) ? 4 : (rnd.nextInt(10) == 0 ? -1 : 0);
                    times.add(new TimeLocation(h[0], h[1], 12, pref, pref, Long.valueOf(1), "Full Term", weeks, 0));
                }
                List<RoomLocation> roomLocs = new ArrayList<RoomLocation>();
                for (RoomConstraint rc: rooms) {
                    if (rc.getCapacity() < limit) continue;
                    int pref = rnd.nextInt(4) == 0 ? -2 : 0;
                    roomLocs.add(new RoomLocation(rc.getResourceId(), rc.getName(), Long.valueOf(1), pref, rc.getCapacity(), 0.0, 0.0, false, rc));
                }
                if (roomLocs.isEmpty())
                    for (RoomConstraint rc: rooms)
                        roomLocs.add(new RoomLocation(rc.getResourceId(), rc.getName(), Long.valueOf(1), 0, rc.getCapacity(), 0.0, 0.0, false, rc));
                Lecture lecture = new Lecture(Long.valueOf(classId++), Long.valueOf(1), Long.valueOf(300 + c), "C" + c + " Lec " + (s + 1),
                        times, roomLocs, 1, null, limit, limit, 1.0);
                lecture.setConfiguration(config);
                config.addTopLecture(lecture);
                model.addVariable(lecture);
                for (RoomLocation rl: roomLocs) rl.getRoomConstraint().addVariable(lecture);
                instructors.get(lectures.size() % instructors.size()).addVariable(lecture);
                lectures.add(lecture);
                sections.add(lecture);
            }
            for (Lecture l: sections) l.setSameSubpartLectures(sections);
            sectionsOf.put(c, sections);
        }

        // cohorts: students of a cohort take the same `take` courses of their block, one section each
        int cohortSize = 40;
        List<Integer> cohortCourses = null;
        List<Integer> cohortSections = null;
        for (int s = 0; s < nrStudents; s++) {
            if (s % cohortSize == 0) {
                int block = rnd.nextInt(nrBlocks);
                List<Integer> pool = new ArrayList<Integer>();
                for (int c = block * coursesPerBlock; c < Math.min(nrCourses, block * coursesPerBlock + coursesPerBlock); c++) pool.add(c);
                java.util.Collections.shuffle(pool, rnd);
                cohortCourses = pool.subList(0, Math.min(pool.size(), take));
                cohortSections = new ArrayList<Integer>();
                for (int c: cohortCourses) cohortSections.add(rnd.nextInt(sectionsOf.get(c).size()));
            }
            Student student = new Student(Long.valueOf(s + 1));
            model.addStudent(student);
            for (int i = 0; i < cohortCourses.size(); i++) {
                int course = cohortCourses.get(i);
                List<Lecture> sections = sectionsOf.get(course);
                Lecture section = sections.get(cohortSections.get(i));
                student.addOffering(configs.get(course).getOfferingId(), 1.0);
                student.addLecture(section);
                student.addConfiguration(section.getConfiguration());
                section.addStudent(assignment, student);
            }
        }
        Map<Lecture, Map<Lecture, JenrlConstraint>> jenrls = new HashMap<Lecture, Map<Lecture, JenrlConstraint>>();
        for (Student st: model.getAllStudents()) {
            for (Lecture l1: st.getLectures()) {
                for (Lecture l2: st.getLectures()) {
                    if (l1.getId() >= l2.getId()) continue;
                    Map<Lecture, JenrlConstraint> x = jenrls.computeIfAbsent(l1, k -> new HashMap<Lecture, JenrlConstraint>());
                    JenrlConstraint j = x.get(l2);
                    if (j == null) {
                        j = new JenrlConstraint();
                        j.addVariable(l1);
                        j.addVariable(l2);
                        model.addConstraint(j);
                        x.put(l2, j);
                    }
                    j.incJenrl(assignment, st);
                }
            }
        }

        Solver<Lecture, Placement> solver = new Solver<Lecture, Placement>(p);
        solver.setInitalSolution(new Solution<Lecture, Placement>(model, assignment));
        out.getAbsoluteFile().getParentFile().mkdirs();
        new TimetableXMLSaver(solver).save(out);
    }
}
