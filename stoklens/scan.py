"""Orkestrasi scan: video -> YOLO track -> embedding match -> OCR -> DB.

CATATAN UNTUK TIM — cara kerja hitungan (anti dobel):
1. Hitungan BUKAN per deteksi, tapi per track ID unik (satu barang yang
   terlihat di 100 frame = 1 track = 1 hitungan).
2. Track umur pendek (< min_track_frames) dibuang — noise / ID pecah sekilas.
3. Tracker default: BoT-SORT + ReID + track_buffer 60 (botsort_reid.yaml)
   — menyambung ID yang putus pakai kemiripan visual.
4. count_mode="line" (default): track hanya dihitung kalau MENYEBERANG garis
   tengah layar searah sweep (lihat crossing.py). Pakai ini untuk rekaman
   sweep sesuai SOP. Untuk kamera statis / video uji meja, pakai
   count_mode="track" (hitung semua track lolos filter).

Parameter yang paling sering perlu di-tuning saat uji lapangan:
- match_threshold : keketatan matching CLIP (turunkan kalau banyak "unknown",
                    naikkan kalau salah-label antar varian)
- min_track_frames: minimal umur track supaya dihitung
- embed_every     : ambil embedding tiap N frame kemunculan (kecil = akurat
                    tapi lambat)
"""
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
from . import db
from .counter import TrackResult, aggregate
from .crossing import count_by_crossing
from .expiry import parse_expiry
from .matcher import match, majority_label
from .ocr import read_text

DEFAULT_TRACKER = str(Path(__file__).with_name("botsort_reid.yaml"))


def run_scan(con, embedder, video_path, model_path="yolo11n.pt",
             match_threshold=0.75, embed_every=5, min_track_frames=3,
             guided_product_id=None, lokasi_rak=None, read_expiry=True,
             count_mode="line", tracker=None):
    """Jalankan scan penuh; return scan_id.

    guided_product_id: guided mode — semua deteksi dianggap kandidat produk ini
                       saja (deklarasi produk per blok, akurasi varian naik).
    count_mode: "line" (rekaman sweep, anti dobel) | "track" (kamera statis).
    tracker: path yaml tracker ultralytics; default BoT-SORT ReID milik StokLens.
    """
    # Lazy import: modul ini harus bisa di-import tanpa torch stack
    # (CI & test monkeypatch run_scan tanpa install ultralytics).
    from ultralytics import YOLO

    products = db.all_products(con)
    allowed = {guided_product_id} if guided_product_id is not None else None
    model = YOLO(model_path)

    seen = defaultdict(int)      # track_id -> jumlah frame terlihat
    embs = defaultdict(list)     # track_id -> daftar embedding sampel
    best_crop = {}               # track_id -> (area, crop) crop terbesar utk OCR
    xhist = defaultdict(list)    # track_id -> riwayat center-x ternormalisasi

    for r in model.track(source=str(video_path), stream=True, persist=True,
                         verbose=False, tracker=tracker or DEFAULT_TRACKER):
        if r.boxes is None or r.boxes.id is None:
            continue
        frame = r.orig_img
        frame_w = frame.shape[1]
        for box, tid in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.int().cpu().tolist()):
            x1, y1, x2, y2 = (max(int(v), 0) for v in box)
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            seen[tid] += 1
            xhist[tid].append(((x1 + x2) / 2) / frame_w)
            area = (x2 - x1) * (y2 - y1)
            if tid not in best_crop or area > best_crop[tid][0]:
                best_crop[tid] = (area, crop.copy())
            if seen[tid] % embed_every == 1:
                embs[tid].append(embedder.embed_bgr(crop))

    # mode line: hanya track yang menyeberang garis searah sweep yang dihitung
    if count_mode == "line":
        counted, _ = count_by_crossing(xhist)
    else:
        counted = {tid: True for tid in seen}

    tracks = []
    for tid, n in seen.items():
        if not embs.get(tid) or not counted.get(tid, False):
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
