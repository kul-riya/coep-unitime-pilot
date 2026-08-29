"""
UniTime Jython Script to Purge Uploaded XML Data.

Upload this file in UniTime:
  Administration > Utilities > Scripts > Add Script
  Engine: Python / Jython
  Permission: Administration or Timetables

Parameters:
# @Input steps: String = "16"
# @Description: Comma-separated list of XML step numbers to purge (e.g. "16" or "12, 13, 16" or "14-16").

Step Numbers Reference:
  1  - Session Setup (Time Patterns, Date Patterns, Subject Areas, Departments)
  2  - Academic Areas
  3  - Academic Classifications
  4  - Majors
  5  - Minors
  6  - Student Groups
  7  - Buildings and Rooms
  8  - Room Sharing
  9  - Travel Times
  10 - Staff / Departmental Instructors
  11 - Course Catalog
  12 - Course Offerings (Instructional Offerings, Configs, Subparts, Classes)
  13 - Preferences
  14 - Student Info
  15 - Student Requests & Demands
  16 - Student Class Enrollments
"""

def get_session_id():
    try:
        if 'session' in globals() and session is not None:
            return session.getUniqueId()
    except Exception:
        pass
    try:
        if 'sessionId' in globals() and sessionId is not None:
            return long(sessionId)
    except Exception:
        pass
    # Fallback to single active session from database
    sessions = hibSession.createQuery("from Session order by sessionBeginDateTime desc").list()
    if sessions:
        return sessions[0].getUniqueId()
    raise Exception("No active Academic Session found.")


def _parse_steps(val):
    """Parse string/int input into a set of step numbers between 1 and 16."""
    if isinstance(val, (int, long)):
        return {int(val)}
    
    text = str(val).strip()
    result = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and bounds[0].strip().isdigit() and bounds[1].strip().isdigit():
                start = int(bounds[0].strip())
                end = int(bounds[1].strip())
                for s in range(min(start, end), max(start, end) + 1):
                    if 1 <= s <= 16:
                        result.add(s)
        elif part.isdigit():
            s = int(part)
            if 1 <= s <= 16:
                result.add(s)
    return result


def purge_solutions_and_timetables(session_id):
    """Delete all saved, committed, and loaded timetable solutions & assignments."""
    log.info("[Pre-check] Purging Saved/Committed Solutions and Assignments...")
    try:
        solutions = hibSession.createQuery(
            "from Solution where owner.session.uniqueId = :sessionId"
        ).setParameter("sessionId", session_id).list()
        
        for sol in solutions:
            try:
                # Uncommit if committed
                if hasattr(sol, "isCommited") and sol.isCommited():
                    if hasattr(sol, "uncommit"):
                        sol.uncommit(hibSession)
                elif hasattr(sol, "isCommitted") and sol.isCommitted():
                    if hasattr(sol, "uncommit"):
                        sol.uncommit(hibSession)
            except Exception as e:
                log.warn("  Could not uncommit solution: %s" % str(e))
            
            try:
                hibSession.delete(sol)
            except Exception as e:
                log.warn("  Could not delete solution: %s" % str(e))
        
        # Clean lingering assignments
        try:
            hibSession.createQuery(
                "delete from ConstraintInfo where assignment.solution.owner.session.uniqueId = :sessionId"
            ).setParameter("sessionId", session_id).executeUpdate()
        except Exception:
            pass
        try:
            hibSession.createQuery(
                "delete from Assignment where solution.owner.session.uniqueId = :sessionId"
            ).setParameter("sessionId", session_id).executeUpdate()
        except Exception:
            pass
        log.info("  Cleaned up %d Solution record(s)." % len(solutions))
    except Exception as e:
        log.warn("  Note during solution cleanup: %s" % str(e))


def step16_remove_student_enrollments(session_id):
    log.info("[Step 16] Purging Student Class Enrollments...")
    count = hibSession.createQuery(
        "delete from StudentClassEnrollment where student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d StudentClassEnrollment records." % count)


def step15_remove_student_requests(session_id):
    log.info("[Step 15] Purging Student Course Demands and Requests...")
    c1 = hibSession.createQuery(
        "delete from CourseRequest where courseDemand.student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c2 = hibSession.createQuery(
        "delete from FreeTime where student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c3 = hibSession.createQuery(
        "delete from CourseDemand where student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d CourseRequests, %d FreeTime, %d CourseDemands." % (c1, c2, c3))


def step14_remove_student_info(session_id):
    log.info("[Step 14] Purging Students and Academic Info...")
    # Remove student associations
    hibSession.createQuery(
        "delete from StudentAreaClassificationMajor where student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    hibSession.createQuery(
        "delete from StudentAreaClassificationMinor where student.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    
    # Delete students
    students = hibSession.createQuery(
        "from Student where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).list()
    for s in students:
        try:
            s.getGroups().clear()
            s.getAccomodations().clear()
            hibSession.delete(s)
        except Exception as e:
            log.warn("  Error deleting student %s: %s" % (str(s.getExternalUniqueId()), str(e)))
    log.info("  Deleted %d Student records." % len(students))


def step13_remove_preferences(session_id):
    log.info("[Step 13] Purging Class and Subpart Preferences...")
    c1 = hibSession.createQuery(
        "delete from DistributionPref where owner.department.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d Distribution Preferences." % c1)


def step12_remove_course_offerings(session_id):
    log.info("[Step 12] Purging Course Offerings, Classes, and Subparts...")
    offerings = hibSession.createQuery(
        "from InstructionalOffering where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).list()
    
    del_count = 0
    for io in offerings:
        try:
            hibSession.delete(io)
            del_count += 1
        except Exception as e:
            log.warn("  Error deleting offering %s: %s" % (str(io.getCourseName()), str(e)))
    log.info("  Deleted %d InstructionalOfferings (with associated Configs, Subparts, and Classes)." % del_count)


def step11_remove_course_catalog(session_id):
    log.info("[Step 11] Purging Course Catalog...")
    c1 = hibSession.createQuery(
        "delete from CourseSubpartCredit where courseCatalog.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c2 = hibSession.createQuery(
        "delete from CourseSubpart where courseCatalog.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c3 = hibSession.createQuery(
        "delete from CourseCatalog where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d CourseCatalog entries." % c3)


def step10_remove_staff(session_id):
    log.info("[Step 10] Purging Departmental Instructors / Staff...")
    c1 = hibSession.createQuery(
        "delete from ClassInstructor where instructor.department.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c2 = hibSession.createQuery(
        "delete from DepartmentalInstructor where department.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d DepartmentalInstructors." % c2)


def step9_remove_travel_times(session_id):
    log.info("[Step 9] Purging Travel Times...")
    c = hibSession.createQuery(
        "delete from TravelTime where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d TravelTime records." % c)


def step8_remove_room_sharing(session_id):
    log.info("[Step 8] Purging Room Sharing / Departments...")
    c = hibSession.createQuery(
        "delete from RoomDept where room.session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d RoomDept records." % c)


def step7_remove_buildings_and_rooms(session_id):
    log.info("[Step 7] Purging Rooms and Buildings...")
    c1 = hibSession.createQuery(
        "delete from Room where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c2 = hibSession.createQuery(
        "delete from NonUniversityLocation where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c3 = hibSession.createQuery(
        "delete from Building where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d Rooms/Locations, %d Buildings." % (c1 + c2, c3))


def step6_remove_student_groups(session_id):
    log.info("[Step 6] Purging Student Groups...")
    groups = hibSession.createQuery(
        "from StudentGroup where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).list()
    for g in groups:
        try:
            g.getStudents().clear()
            hibSession.delete(g)
        except Exception as e:
            log.warn("  Error deleting student group %s: %s" % (str(g.getGroupValue()), str(e)))
    log.info("  Deleted %d StudentGroups." % len(groups))


def step5_remove_minors(session_id):
    log.info("[Step 5] Purging Academic Minors...")
    c = hibSession.createQuery(
        "delete from PosMinor where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d PosMinors." % c)


def step4_remove_majors(session_id):
    log.info("[Step 4] Purging Academic Majors...")
    c = hibSession.createQuery(
        "delete from PosMajor where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d PosMajors." % c)


def step3_remove_academic_classifications(session_id):
    log.info("[Step 3] Purging Academic Classifications...")
    c = hibSession.createQuery(
        "delete from AcademicClassification where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d AcademicClassifications." % c)


def step2_remove_academic_areas(session_id):
    log.info("[Step 2] Purging Academic Areas...")
    c = hibSession.createQuery(
        "delete from AcademicArea where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d AcademicAreas." % c)


def step1_remove_session_setup(session_id):
    log.info("[Step 1] Purging Session Setup (Time Patterns, Date Patterns, Subject Areas, Departments)...")
    c1 = hibSession.createQuery(
        "delete from TimePattern where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c2 = hibSession.createQuery(
        "delete from DatePattern where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c3 = hibSession.createQuery(
        "delete from SubjectArea where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    c4 = hibSession.createQuery(
        "delete from Department where session.uniqueId = :sessionId"
    ).setParameter("sessionId", session_id).executeUpdate()
    log.info("  Deleted %d TimePatterns, %d DatePatterns, %d SubjectAreas, %d Departments." % (c1, c2, c3, c4))


# Step runners in reverse dependency order (16 down to 1)
STEP_CLEANERS = [
    (16, step16_remove_student_enrollments),
    (15, step15_remove_student_requests),
    (14, step14_remove_student_info),
    (13, step13_remove_preferences),
    (12, step12_remove_course_offerings),
    (11, step11_remove_course_catalog),
    (10, step10_remove_staff),
    (9,  step9_remove_travel_times),
    (8,  step8_remove_room_sharing),
    (7,  step7_remove_buildings_and_rooms),
    (6,  step6_remove_student_groups),
    (5,  step5_remove_minors),
    (4,  step4_remove_majors),
    (3,  step3_remove_academic_classifications),
    (2,  step2_remove_academic_areas),
    (1,  step1_remove_session_setup),
]


def execute():
    # Retrieve input step numbers
    raw_steps = "16"
    try:
        if 'steps' in globals() and steps is not None:
            raw_steps = steps
        elif 'from_step' in globals() and from_step is not None:
            raw_steps = from_step
    except Exception:
        pass
    
    target_steps = _parse_steps(raw_steps)
    if not target_steps:
        log.error("No valid step numbers found in input: %r. Please specify numbers between 1 and 16." % str(raw_steps))
        return
    
    session_id = get_session_id()
    log.info("=======================================================================")
    log.info("Starting Data Purge for Selected Step(s): %s (Session ID: %s)" % (
        ", ".join(str(s) for s in sorted(target_steps)), str(session_id)
    ))
    log.info("=======================================================================")
    
    tx = None
    we_started_tx = False
    try:
        # Handle transactions safely (avoid IllegalStateException if already active)
        if hasattr(hibSession, "getTransaction"):
            current_tx = hibSession.getTransaction()
            if current_tx and current_tx.isActive():
                tx = current_tx
                we_started_tx = False
            else:
                tx = hibSession.beginTransaction()
                we_started_tx = True
        elif hasattr(hibSession, "beginTransaction"):
            tx = hibSession.beginTransaction()
            we_started_tx = True
        
        # If any offering/class/room step is targeted, first purge any saved/committed solutions & assignments
        needs_solution_purge = any(s in target_steps for s in (1, 2, 7, 8, 10, 11, 12, 13, 16))
        if needs_solution_purge:
            purge_solutions_and_timetables(session_id)
        
        # Execute cleaners ONLY for the target steps in reverse dependency order (16 down to 1)
        executed = 0
        for num, cleaner_fn in STEP_CLEANERS:
            if num in target_steps:
                cleaner_fn(session_id)
                executed += 1
        
        hibSession.flush()
        if we_started_tx and tx:
            tx.commit()
        log.info("=======================================================================")
        log.info("Successfully purged data for %d selected step(s)." % executed)
        log.info("=======================================================================")
    except Exception as e:
        if we_started_tx and tx:
            try:
                tx.rollback()
            except Exception:
                pass
        log.error("Data purge failed: " + str(e))
        raise e

if __name__ == '__main__':
    execute()
