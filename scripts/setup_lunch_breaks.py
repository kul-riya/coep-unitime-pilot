"""
UniTime Jython Script to configure Student and Instructor Lunch Breaks.
Upload this file in Administration > Utilities > Scripts and execute it.
"""

from org.unitime.timetable.model import SolverParameterGroup, SolverParameterDef
from org.unitime.timetable.model.dao import SolverParameterGroupDAO, SolverParameterDefDAO

def get_or_create_group(name, description, order):
    # Find existing group
    groups = hibSession.createQuery("from SolverParameterGroup where name = :name").setString("name", name).list()
    if groups:
        return groups[0]
    
    # Create new group
    group = SolverParameterGroup()
    group.setName(name)
    group.setDescription(description)
    group.setOrder(order)
    hibSession.save(group)
    return group

def get_or_create_param(group, name, default_value, description, p_type, order):
    params = hibSession.createQuery("from SolverParameterDef where name = :name").setString("name", name).list()
    if params:
        param = params[0]
        param.setDefault(default_value)
        hibSession.update(param)
        return param
    
    param = SolverParameterDef()
    param.setName(name)
    param.setDefault(default_value)
    param.setDescription(description)
    param.setType(p_type)
    param.setOrder(order)
    param.setGroup(group)
    param.setVisible(True)
    hibSession.save(param)
    return param

def append_to_additional_criteria(criterion_class):
    params = hibSession.createQuery("from SolverParameterDef where name = 'General.AdditionalCriteria'").list()
    if params:
        param = params[0]
        current_default = param.getDefault()
        if current_default is None:
            current_default = ""
        
        if criterion_class not in current_default:
            new_default = current_default
            if len(new_default) > 0 and not new_default.endswith(";"):
                new_default += ";"
            new_default += criterion_class
            param.setDefault(new_default)
            hibSession.update(param)
            log.info("Appended " + criterion_class + " to General.AdditionalCriteria")
        else:
            log.info(criterion_class + " is already in General.AdditionalCriteria")

def execute():
    log.info("Starting Lunch Breaks configuration...")
    
    # 1. Enable Student Lunch Break in Additional Criteria
    append_to_additional_criteria("org.cpsolver.coursett.criteria.additional.StudentLuchBreak")
    # Enable Instructor Lunch Break
    append_to_additional_criteria("org.cpsolver.coursett.criteria.additional.InstructorLunchBreak")

    # Group for Student Lunch Breaks
    student_group = get_or_create_group("StudentLunch", "Student Lunch Breaks", 100)
    
    # 11:30 AM = 138 (since 138 * 5 / 60 = 11.5)
    # 3:30 PM = 15:30 = 186 (since 186 * 5 / 60 = 15.5)
    # 1 hour break = 12 slots
    
    # Student Lunch Parameters
    get_or_create_param(student_group, "StudentLunch.StartSlot", "138", "Student lunch period start time (5 min slots)", "integer", 1)
    get_or_create_param(student_group, "StudentLunch.EndStart", "186", "Student lunch period end time (5 min slots)", "integer", 2)
    get_or_create_param(student_group, "StudentLunch.Length", "12", "Minimal length of a student lunch break (5 min slots)", "integer", 3)
    
    # Group for Instructor Lunch Breaks
    instructor_group = get_or_create_group("InstructorLunch", "Instructor Lunch Breaks", 101)
    
    # Instructor Lunch Parameters
    get_or_create_param(instructor_group, "InstructorLunch.Enabled", "true", "Enable Instructor Lunch Breaks", "boolean", 1)
    get_or_create_param(instructor_group, "InstructorLunch.Weight", "0.18", "Instructor Lunch Break Weight", "double", 2)
    get_or_create_param(instructor_group, "InstructorLunch.StartSlot", "138", "Instructor lunch period start time (5 min slots)", "integer", 3)
    get_or_create_param(instructor_group, "InstructorLunch.EndSlot", "186", "Instructor lunch period end time (5 min slots)", "integer", 4)
    get_or_create_param(instructor_group, "InstructorLunch.Length", "12", "Minimal length of an instructor lunch break (5 min slots)", "integer", 5)
    get_or_create_param(instructor_group, "InstructorLunch.ViolationsMultiplicationFactor", "1.15", "Violations multiplication factor", "double", 6)
    get_or_create_param(instructor_group, "InstructorLunch.ShowViolations", "true", "Show violations in the solution info", "boolean", 7)
    
    log.info("Lunch Breaks configuration completed successfully.")

if __name__ == '__main__':
    execute()
