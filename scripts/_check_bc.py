"""Quick check of batchClass mapping."""
import sys; sys.path.insert(0, '.')
from taasika_loader import load
from collections import defaultdict

data = load(snapshot_id=240, tables=['batchClass','batch','class','subjectBatchTeacher','subjectClassTeacher'])
bc = data.filtered('batchClass')
batch2class = {}
class2batches = defaultdict(list)
for row in bc:
    batch2class[row['batchId']] = row['classId']
    class2batches[row['classId']].append(row['batchId'])

batches = {b['batchId']: b for b in data.filtered('batch')}
classes = {c['classId']: c for c in data.filtered('class')}

print(f"Total batch->class mappings: {len(batch2class)}")
print(f"Total classes with batches: {len(class2batches)}")
print()

for cid in sorted(class2batches.keys())[:6]:
    cls = classes.get(cid, {})
    cname = cls.get('classShortName', '?')
    bnames = [batches.get(bid, {}).get('batchName', '?') for bid in class2batches[cid]]
    print(f"  Class {cid} ({cname}): {len(bnames)} batches: {bnames}")

print()
sbt = data.filtered('subjectBatchTeacher')
sbt_batch_ids = set(row['batchId'] for row in sbt)
missing = sbt_batch_ids - set(batch2class.keys())
print(f"Batches in SBT: {len(sbt_batch_ids)}")
print(f"Batches in SBT not in batchClass: {len(missing)}")
if missing:
    for bid in sorted(missing)[:5]:
        b = batches.get(bid, {})
        print(f"  Missing: batch {bid} ({b.get('batchName', '?')})")

# Also check: for an SCT row, does every classId have batches?
sct = data.filtered('subjectClassTeacher')
sct_class_ids = set(row['classId'] for row in sct)
print(f"\nClasses in SCT: {len(sct_class_ids)}")
classes_with_batches = sct_class_ids & set(class2batches.keys())
classes_without_batches = sct_class_ids - set(class2batches.keys())
print(f"SCT classes WITH batches in batchClass: {len(classes_with_batches)}")
print(f"SCT classes WITHOUT batches in batchClass: {len(classes_without_batches)}")
if classes_without_batches:
    for cid in sorted(classes_without_batches)[:5]:
        cls = classes.get(cid, {})
        print(f"  No batches: class {cid} ({cls.get('classShortName', '?')})")
