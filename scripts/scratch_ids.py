import json

idx = json.loads(open("scripts/offering_index.json", "r", encoding="utf-8").read())
si = json.loads(open("scripts/subject_index.json", "r", encoding="utf-8").read())

# Find PP(FY) subjects
pp_sids = [sid for sid, info in si.items() if "PP(FY)" in info.get("shortName", "")]
print("PP(FY) subjects:")
for s in pp_sids:
    info = si[s]
    print(f"  sid={s} short={info['shortName']} isLab={info.get('isLab')} "
          f"primarySubjectId={info.get('primarySubjectId')} courseNbr={info['courseNumber']}")

# Check lec_to_lab mapping
l2l = idx["lec_to_lab"]
print(f"\nlec_to_lab for PP(FY) sids:")
for s in pp_sids:
    if s in l2l:
        print(f"  {s} -> {l2l[s]}")
    for k, v in l2l.items():
        if str(v) == s:
            print(f"  {k} -> {v}  (PP-Lab is target)")

# Check parent_child
pc = idx["parent_child"]
print(f"\nparent_child for PP(FY):")
for s in pp_sids:
    if not si[s].get("isLab"):
        result = pc.get(s, "NOT FOUND")
        print(f"  pc[{s}] = {result}")

# Check what _constrained_labs receives
# In class_tags_for_short, line 246: _constrained_labs(sid, ...)
# sid = the subject ID from by_short[short]
# For "PP(FY)" short, sid = PP(FY)'s subjectId
# For "PP(FY)-Lab" short, sid = PP(FY)-Lab's subjectId
print(f"\n--- Call trace for class_tags_for_short('PP(FY)') ---")
pp_lec_sid = [s for s in pp_sids if not si[s].get("isLab")]
pp_lab_sid = [s for s in pp_sids if si[s].get("isLab")]
if pp_lec_sid:
    lec_sid = pp_lec_sid[0]
    print(f"  short='PP(FY)', sid={lec_sid}")
    print(f"  Line 246: _constrained_labs(sid={lec_sid}, ...)")
    print(f"  Inside _constrained_labs: offering_key = str({lec_sid}) = '{lec_sid}'")
    print(f"  pc.get('{lec_sid}') = {pc.get(lec_sid, 'NOT FOUND')}")

print(f"\n--- Call trace for auto-partner (line 266) ---")
if pp_lec_sid:
    lec_sid = pp_lec_sid[0]
    print(f"  short='PP(FY)', sid={lec_sid}")
    print(f"  Finding lab partner with primarySubjectId == {lec_sid}")
    if pp_lab_sid:
        lab_sid = pp_lab_sid[0]
        print(f"  Found: '{si[lab_sid]['shortName']}' (sid={lab_sid})")
        print(f"  Line 266: _constrained_labs(sid={lec_sid}, ...)")
        print(f"  Inside: offering_key = '{lec_sid}', pc.get('{lec_sid}') = {pc.get(lec_sid, 'NOT FOUND')}")

# Now check what the section_offsets look like for PP(FY)
print(f"\n--- Section offsets for PP(FY) ---")
offsets = idx["section_offsets"]
for k, v in sorted(offsets.items()):
    for s in pp_sids:
        if k.startswith(f"{s}|"):
            print(f"  {k} = {v}")
