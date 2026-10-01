import sys
import csv
from pathlib import Path
from collections import defaultdict
import datetime
import json

def parse_time(t_str):
    """Convert '2:30p' to minutes from midnight."""
    t_str = t_str.strip().lower()
    is_pm = 'p' in t_str
    t_str = t_str.replace('a', '').replace('p', '').strip()
    parts = t_str.split(':')
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    if is_pm and h != 12:
        h += 12
    if not is_pm and h == 12:
        h = 0
    return h * 60 + m

def format_time(minutes):
    """Convert minutes to '2:30 PM' string."""
    h = minutes // 60
    m = minutes % 60
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0: h12 = 12
    return f"{h12}:{m:02d} {ap}"

def generate_html(csv_path, html_path):
    classes = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            days = row.get("DAY", "").strip()
            # Handle multiple days (e.g. MWF)
            parsed_days = []
            if "M" in days: parsed_days.append("Monday")
            if "T" in days and "Th" not in days: parsed_days.append("Tuesday")
            if "T" in days and "Th" in days and days.count("T") > 1: parsed_days.append("Tuesday")
            if "T" in days and "Th" not in days: parsed_days.append("Tuesday")
            
            # Better day parsing for MTWThFS
            day_map = []
            dstr = days
            while dstr:
                if dstr.startswith('Th'): day_map.append("Thursday"); dstr = dstr[2:]
                elif dstr.startswith('T'): day_map.append("Tuesday"); dstr = dstr[1:]
                elif dstr.startswith('M'): day_map.append("Monday"); dstr = dstr[1:]
                elif dstr.startswith('W'): day_map.append("Wednesday"); dstr = dstr[1:]
                elif dstr.startswith('F'): day_map.append("Friday"); dstr = dstr[1:]
                elif dstr.startswith('Su'): day_map.append("Sunday"); dstr = dstr[2:]
                elif dstr.startswith('S'): day_map.append("Saturday"); dstr = dstr[1:]
                else:
                    dstr = dstr[1:] # fallback

            start_t = parse_time(row.get("START_TIME", ""))
            end_t = parse_time(row.get("END_TIME", ""))
            
            for d in day_map:
                classes.append({
                    "id": row.get("CLASS_ID", ""),
                    "title": row.get("CLASS", ""),
                    "note": row.get("SCHEDULE_NOTE", ""),
                    "day": d,
                    "start": start_t,
                    "end": end_t,
                    "start_str": format_time(start_t),
                    "end_str": format_time(end_t),
                    "room": row.get("ROOM", ""),
                    "instructor": row.get("INSTRUCTOR", ""),
                    "limit": row.get("LIMIT", "")
                })

    # Prepare JSON data for the frontend
    classes_json = json.dumps(classes)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Timetable Visualization</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f6fa;
            color: #2f3640;
        }}
        h1 {{
            text-align: center;
            color: #273c75;
        }}
        .controls {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 20px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        select, input {{
            padding: 8px 12px;
            border: 1px solid #dcdde1;
            border-radius: 4px;
            font-size: 14px;
        }}
        .grid-container {{
            display: grid;
            grid-template-columns: 80px repeat(6, 1fr);
            gap: 2px;
            background: #dcdde1;
            border: 1px solid #dcdde1;
        }}
        .header {{
            background: #273c75;
            color: white;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }}
        .time-label {{
            background: #f5f6fa;
            border-bottom: 1px solid #dcdde1;
            text-align: right;
            padding-right: 5px;
            font-size: 12px;
            color: #718093;
            height: 30px; /* 30 mins */
            box-sizing: border-box;
            transform: translateY(-50%);
        }}
        .day-column {{
            background: white;
            position: relative;
        }}
        .class-card {{
            position: absolute;
            left: 2px;
            right: 2px;
            background: #00a8ff;
            color: white;
            padding: 5px;
            border-radius: 4px;
            font-size: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            border-left: 4px solid #0097e6;
            cursor: pointer;
            transition: transform 0.1s;
        }}
        .class-card:hover {{
            transform: scale(1.02);
            z-index: 100 !important;
        }}
        .class-title {{
            font-weight: bold;
            margin-bottom: 3px;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
        }}
        .class-details {{
            font-size: 11px;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <h1>Interactive Timetable</h1>
    <div class="controls">
        <select id="filter-type">
            <option value="room">By Room</option>
            <option value="instructor">By Instructor</option>
            <option value="course">By Course Group (Note)</option>
        </select>
        <select id="filter-value">
            <option value="all">All (Warning: Overlaps)</option>
        </select>
    </div>

    <div id="timetable" style="position: relative; display: flex; background: white; border: 1px solid #dcdde1;">
        <!-- Timetable will be rendered here via JS -->
    </div>

    <script>
        const rawData = {classes_json};
        
        // Colors mapping for visual distinction
        const colors = ['#00a8ff', '#9c88ff', '#fbc531', '#4cd137', '#487eb0', '#e84118', '#8c7ae6', '#e1b12c'];
        
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const startMin = 7 * 60; // 7:00 AM
        const endMin = 20 * 60;  // 8:00 PM
        const pixelsPerMinute = 1.5;

        function init() {{
            populateFilters();
            document.getElementById('filter-type').addEventListener('change', populateFilters);
            document.getElementById('filter-value').addEventListener('change', renderTimetable);
            renderTimetable();
        }}

        function populateFilters() {{
            const type = document.getElementById('filter-type').value;
            const valueSelect = document.getElementById('filter-value');
            
            const uniqueVals = [...new Set(rawData.map(d => {{
                if (type === 'room') return d.room;
                if (type === 'instructor') return d.instructor;
                if (type === 'course') return d.note || d.title.split(' ')[1]; // rough group
                return '';
            }}))].filter(Boolean).sort();

            valueSelect.innerHTML = '<option value="all">All</option>';
            uniqueVals.forEach(v => {{
                valueSelect.innerHTML += `<option value="${{v}}">${{v}}</option>`;
            }});
        }}

        function renderTimetable() {{
            const type = document.getElementById('filter-type').value;
            const filterVal = document.getElementById('filter-value').value;

            let filtered = rawData;
            if (filterVal !== 'all') {{
                filtered = rawData.filter(d => {{
                    if (type === 'room') return d.room === filterVal;
                    if (type === 'instructor') return d.instructor === filterVal;
                    if (type === 'course') return (d.note === filterVal) || (d.title.split(' ')[1] === filterVal);
                }});
            }}

            const container = document.getElementById('timetable');
            container.innerHTML = '';

            // Render Time Axis
            const timeAxis = document.createElement('div');
            timeAxis.style.width = '80px';
            timeAxis.style.borderRight = '1px solid #dcdde1';
            timeAxis.style.position = 'relative';
            timeAxis.style.height = `${{(endMin - startMin) * pixelsPerMinute}}px`;
            
            for (let m = startMin; m <= endMin; m += 60) {{
                const label = document.createElement('div');
                label.className = 'time-label';
                label.style.position = 'absolute';
                label.style.top = `${{(m - startMin) * pixelsPerMinute}}px`;
                label.style.width = '100%';
                
                const h = Math.floor(m / 60);
                const ap = h < 12 ? 'AM' : 'PM';
                const h12 = h % 12 === 0 ? 12 : h % 12;
                label.innerText = `${{h12}}:00 ${{ap}}`;
                timeAxis.appendChild(label);
                
                // grid line
                const line = document.createElement('div');
                line.style.position = 'absolute';
                line.style.top = `${{(m - startMin) * pixelsPerMinute}}px`;
                line.style.left = '80px';
                line.style.right = '0';
                line.style.height = '1px';
                line.style.background = '#f5f6fa';
                line.style.zIndex = '0';
                container.appendChild(line);
            }}
            container.appendChild(timeAxis);

            // Render Day Columns
            days.forEach((day, dayIdx) => {{
                const col = document.createElement('div');
                col.style.flex = '1';
                col.style.borderRight = '1px solid #dcdde1';
                col.style.position = 'relative';
                
                const header = document.createElement('div');
                header.className = 'header';
                header.innerText = day;
                header.style.position = 'absolute';
                header.style.top = '-40px';
                header.style.left = '0';
                header.style.right = '0';
                col.appendChild(header);

                // Add classes for this day
                const dayClasses = filtered.filter(c => c.day === day);
                
                // Very basic overlap handling (staggering visually)
                const sorted = dayClasses.sort((a,b) => a.start - b.start);
                let currentZ = 10;
                
                sorted.forEach(c => {{
                    const card = document.createElement('div');
                    card.className = 'class-card';
                    card.style.top = `${{(c.start - startMin) * pixelsPerMinute}}px`;
                    card.style.height = `${{(c.end - c.start) * pixelsPerMinute}}px`;
                    card.style.zIndex = currentZ++;
                    
                    // Assign color based on course title prefix
                    const colorIdx = c.title.charCodeAt(3) % colors.length || 0;
                    card.style.background = colors[colorIdx];
                    card.style.borderLeftColor = '#2f3640';

                    card.innerHTML = `
                        <div class="class-title" title="${{c.title}}">${{c.title}}</div>
                        <div class="class-details">${{c.start_str}} - ${{c.end_str}}</div>
                        <div class="class-details">${{c.room}}</div>
                        <div class="class-details">${{c.instructor}}</div>
                    `;
                    col.appendChild(card);
                }});

                container.appendChild(col);
            }});
            
            container.style.marginTop = '40px'; // make room for headers
        }}

        init();
    </script>
</body>
</html>
"""

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Generated HTML timetable at {html_path}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 generate_timetable_html.py <input.csv> <output.html>")
        sys.exit(1)
    generate_html(sys.argv[1], sys.argv[2])
