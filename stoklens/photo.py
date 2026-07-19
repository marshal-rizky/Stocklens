"""Photo mode: opname via foto per segmen rak (tanpa tracking).

KENAPA MODE INI ADA
-------------------
- Dalam 1 foto, 1 deteksi = 1 barang — kelas masalah "ID pecah / dobel hitung"
  milik video tidak eksis di sini.
- Jauh lebih murah: 6 foto ±18 MB vs video ±75 MB; deteksi 6 gambar vs 60 frame.
- OCR expired lebih akurat: foto diam tajam, frame video blur gerakan.

ANTI-DOBEL ANTAR FOTO
---------------------
Risiko pindah ke antar-foto (zona overlap kehitung 2x). Mitigasi:
1. SOP: 1 foto = 1 sub-segmen berbatas fisik (tiang/sekat rak), jangan overlap.
2. Hasil menyertakan breakdown `per_foto` -> UI menampilkan hitungan per foto,
   user bisa melihat dan mengoreksi dobel/gap secara visual.
3. (Roadmap) stitching antar foto + dedup homography.

`detector` dan `embedder` injectable — test memakai fake, CI tidak butuh torch.
"""
from collections import defaultdict
from datetime import date

import cv2

from . import crops, db
from .expiry import parse_expiry
from .matcher import match


def aggregate_detections(detections):
    """detections: list (foto_idx, product_id|None, score).

    Return {product_id|'unknown': {qty, confidence_avg, per_foto}} dengan
    per_foto = {foto_idx: jumlah} untuk review visual anti-dobel di UI.
    """
    out = {}
    for foto_idx, pid, score in detections:
        key = pid if pid is not None else "unknown"
        d = out.setdefault(key, {"qty": 0, "_scores": [],
                                 "per_foto": defaultdict(int)})
        d["qty"] += 1
        d["_scores"].append(score)
        d["per_foto"][foto_idx] += 1
    for d in out.values():
        d["confidence_avg"] = round(sum(d.pop("_scores")) / d["qty"], 3)
        d["per_foto"] = dict(d["per_foto"])
    return out


def _yolo_detector(model_path="yolo11n.pt"):
    """Detector default (lazy import — modul ini tetap ringan tanpa torch)."""
    from ultralytics import YOLO
    model = YOLO(model_path)

    def detect(image_bgr):
        r = model.predict(image_bgr, verbose=False)[0]
        if r.boxes is None:
            return []
        return [tuple(map(int, b)) for b in r.boxes.xyxy.cpu().numpy()]

    return detect


def scan_photos(con, embedder, images, detector=None, match_threshold=0.75,
                guided_product_id=None, lokasi_rak=None, read_expiry=True,
                simpan_unknown=True, maks_unknown=30, dir_crops=None):
    """Opname dari kumpulan foto; return scan_id (scans.tipe = 'foto').

    images: list np.ndarray BGR atau path file gambar.
    detector: fn(image_bgr) -> list (x1, y1, x2, y2); default YOLO.
    guided_product_id: guided mode — semua deteksi kandidat produk ini saja.
    simpan_unknown: simpan crop deteksi tak dikenali ke `unknown_crops` supaya
                   bisa diberi nama user nanti (Unit 3). Maks `maks_unknown`
                   crop per scan — sebelum YOLO di-fine-tune hampir semua
                   deteksi "unknown", jangan sampai membanjiri disk.
    dir_crops: direktori dasar file crop; default crops.DIR_CROPS_DEFAULT.
    """
    products = db.all_products(con, with_gallery=True)
    allowed = {guided_product_id} if guided_product_id is not None else None
    detect = detector or _yolo_detector()

    detections = []          # (foto_idx, product_id|None, score)
    crops_per_product = defaultdict(list)   # pid -> crops utk OCR expired
    # (crop, embedding) unknown menunggu disimpan — ditunda karena scan_id
    # baru ada setelah db.add_scan() di bawah (perlu utk foreign key & path).
    unknown_buffer = []
    for i, img in enumerate(images):
        if not hasattr(img, "shape"):
            img = cv2.imread(str(img))
            if img is None:
                raise FileNotFoundError(f"Foto tidak bisa dibaca: {images[i]}")
        for x1, y1, x2, y2 in detect(img):
            crop = img[max(y1, 0):y2, max(x1, 0):x2]
            if crop.size == 0:
                continue
            embedding = embedder.embed_bgr(crop)
            pid, score = match(embedding, products,
                               threshold=match_threshold, allowed_ids=allowed)
            detections.append((i, pid, score))
            if pid is not None:
                crops_per_product[pid].append(crop)
            elif simpan_unknown and len(unknown_buffer) < maks_unknown:
                # .copy(): crop adalah view ke foto resolusi penuh — tanpa copy
                # seluruh foto ikut tertahan di RAM sampai loop persist.
                unknown_buffer.append((crop.copy(), embedding))

    counts = aggregate_detections(detections)

    expiry_per_product = defaultdict(list)
    if read_expiry:
        from .ocr import read_text
        for pid, crop_list in crops_per_product.items():
            for crop in crop_list:
                d = parse_expiry(read_text(crop))
                if d:
                    expiry_per_product[pid].append(d)

    scan_id = db.add_scan(con, lokasi_rak=lokasi_rak, tipe="foto")
    crops.simpan_buffer(con, scan_id, unknown_buffer, dir_crops)

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
