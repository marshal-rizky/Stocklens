"""PoC: hitung objek unik per kelas COCO di sebuah video.

Pakai: python scripts/poc_track.py video_rak.mp4
"""
import sys
from collections import defaultdict

from ultralytics import YOLO

video = sys.argv[1]
model = YOLO("yolo11n.pt")
ids_per_class = defaultdict(set)
for r in model.track(source=video, stream=True, persist=True, verbose=False):
    if r.boxes is None or r.boxes.id is None:
        continue
    for cls, tid in zip(r.boxes.cls.int().tolist(), r.boxes.id.int().tolist()):
        ids_per_class[model.names[cls]].add(tid)

print(f"\nHasil hitung objek unik di {video}:")
for name, ids in sorted(ids_per_class.items(), key=lambda kv: -len(kv[1])):
    print(f"  {name}: {len(ids)}")
