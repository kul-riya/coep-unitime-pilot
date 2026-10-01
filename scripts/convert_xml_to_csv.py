import sys
import xml.etree.ElementTree as ET
import csv
import re

def parse_class_name(name):
    """
    Parses a class name like 'CS AI Lec 1' into ('CS AI', 'Lec', '1').
    """
    match = re.search(r'\s+(Lec|Lab|Rec|Tut|Prac)\s+(\d+)$', name, re.IGNORECASE)
    if match:
        course = name[:match.start()].strip()
        itype = match.group(1).capitalize()
        section = match.group(2)
        return course, itype, section
    return name, "", ""

def format_instructor(name):
    """
    Formats 'Vahida Attar' into 'Attar, V'.
    If there's only one word, returns it.
    """
    if not name:
        return ""
    parts = name.strip().split()
    if len(parts) >= 2:
        firsts = "".join([p[0] + " " for p in parts[:-1]]).strip()
        last = parts[-1]
        return f"{last}, {firsts}"
    return name

def get_days_string(days):
    """
    Converts '0111000' into 'TWTh'.
    """
    mapping = ["M", "T", "W", "Th", "F", "S", "Su"]
    res = "".join(m for d, m in zip(days, mapping) if d == '1')
    if res == "MTWThF":
        return "MTWThF"  # Just to note typical cases
    return res

def format_time(start_idx, length_idx):
    """
    Converts 5-min increments from midnight to am/pm strings.
    start='150', length='12' -> 12:30p to 1:30p.
    """
    start_mins = int(start_idx) * 5
    end_mins = start_mins + int(length_idx) * 5
    
    def to_ampm(mins):
        h = mins // 60
        m = mins % 60
        ap = "a" if h < 12 else "p"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{m:02d}{ap}"
        
    return to_ampm(start_mins), to_ampm(end_mins)

def convert(xml_path, csv_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Build dictionaries for rooms and instructors
    rooms = {}
    for r in root.findall('.//rooms/room'):
        rooms[r.get('id')] = r.get('name')
        
    instructors = {}
    for i in root.findall('.//instructors/instructor'):
        instructors[i.get('id')] = i.get('name')
        
    rows = []
    
    for cl in root.findall('.//class'):
        name = cl.get('name')
        if not name:
            continue
            
        course, itype, section = parse_class_name(name)
        
        times = cl.findall('.//time[@solution="true"]')
        if not times:
            # Skip if this class isn't assigned
            continue
            
        time_node = times[0]
        days = get_days_string(time_node.get('days', '0000000'))
        start_t, end_t = format_time(time_node.get('start', '0'), time_node.get('length', '0'))
        
        room_nodes = cl.findall('.//room[@solution="true"]')
        room_names = [rooms.get(r.get('id'), '') for r in room_nodes]
        room_str = ", ".join(filter(None, room_names))
        
        instructor_nodes = cl.findall('.//instructor[@solution="true"]')
        instructor_names = [format_instructor(instructors.get(i.get('id'), '')) for i in instructor_nodes]
        instructor_str = ", ".join(filter(None, instructor_names))
        
        row = {
            "COURSE": course,
            "ITYPE": itype,
            "SECTION": section,
            "SUFFIX": "",
            "EXT_ID": "",
            "DATE_PATTERN": "Full Term",  # Defaulting as per the requested CSV
            "DAY": days,
            "START_TIME": start_t,
            "END_TIME": end_t,
            "ROOM": room_str,
            "INSTRUCTOR": instructor_str
        }
        rows.append(row)
        
    # Sort for consistent output
    def sort_key(r):
        sec = r["SECTION"]
        return (r["COURSE"], r["ITYPE"], int(sec) if sec.isdigit() else sec)
        
    rows.sort(key=sort_key)
    
    fieldnames = [
        "COURSE", "ITYPE", "SECTION", "SUFFIX", "EXT_ID", 
        "DATE_PATTERN", "DAY", "START_TIME", "END_TIME", 
        "ROOM", "INSTRUCTOR"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Successfully converted {xml_path} to {csv_path}")

if __name__ == '__main__':
    xml_path = ""
    csv_path = ""
    
    if len(sys.argv) >= 3:
        xml_path = sys.argv[1]
        csv_path = sys.argv[2]
    else:
        xml_path = input("Enter the path to the input XML solution file: ").strip()
        csv_path = input("Enter the path to the output CSV file: ").strip()
        
    if not xml_path or not csv_path:
        print("Both input XML and output CSV paths are required.")
        sys.exit(1)
        
    convert(xml_path, csv_path)
