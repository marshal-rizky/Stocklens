"""Orkestrasi scan: video -> YOLO track -> embedding match -> OCR -> DB."""
from collections import defaultdict
from datetime import date

import numpy as np
from ultralytics import YOLO

from . import db
from .counter import TrackResult, aggregate
from .expiry import parse_expiry
from .matcher import match, majority_label
from .ocr import read_text


def run_scan(con, embedder, video_path, model_path="yolo11n.pt",
             match_threshold=0.75, embed_every=5, min_track_frames=3,
             guided_product_id=None, lokasi_rak=None, read_expiry=True):
    """Jalankan scan penuh; return scan_id.

    guided_product_id: guided mode — semua deteksi dianggap kandidat produk ini saja.
    """
    products = db.all_products(con)
    allowed = {guided_product_id} if guided_product_id is not None else None
    model = YOLO(model_path)

    seen = defaultdict(int)      # track_id -> jumlah frame terlihat
    embs = defaultdict(list)     # track_id -> daftar embedding sampel
    best_crop = {}               # track_id -> (area, crop) crop terbesar utk OCR

    for r in model.track(source=str(video_path), stream=True, persist=True, verbose=False):
        if r.boxes is None or r.boxes.id is None:
            continue
        frame = r.orig_img
        for box, tid in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.int().cpu().tolist()):
            x1, y1, x2, y2 = (max(int(v), 0) for v in box)
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            seen[tid] += 1
            area = (x2 - x1) * (y2 - y1)
            if tid not in best_crop or area > best_crop[tid][0]:
                best_crop[tid] = (area, crop.copy())
            if seen[tid] % embed_every == 1:
                embs[tid].append(embedder.embed_bgr(crop))

    tracks = []
    for tid, n in seen.items():
        if not embs.get(tid):
            continue
        labels, scores = [], []
        for e in embs[tid]:
            pid, s = match(e, products, threshold=match_threshold, allowed_ids=allowed)
            labels.append(pid)
            scores.append(s)
        tracks.append(TrackResult(tid, majority_label(labels),
                                  round(float(np.mean(scores)), 3), n))

    counts = aggregate(tracks, min_track_frames=min_track_frames)

    expiry_per_product = defaultdict(list)
    if read_expiry:
        for t in tracks:
            if t.product_id is None or t.n_frames < min_track_frames:
                continue
            d = parse_expiry(read_text(best_crop[t.track_id][1]))
            if d:
                expiry_per_product[t.product_id].append(d)

    scan_id = db.add_scan(con, video_ref=str(video_path), lokasi_rak=lokasi_rak)
    today = date.today()
    for pid, c in counts.items():
        if pid == "unknown":
            db.add_scan_item(con, scan_id, None, c["qty"], c["confidence_avg"])
            continue
        dates = sorted(expiry_per_product.get(pid, []))
        db.add_scan_item(
            con, scan_id, pid, c["qty"], c["confidence_avg"],
            expired_terdekat=dates[0].isoformat() if dates else None,
            qty_expired=sum(1 for d in dates if d <= today),
        )
    return scan_id
