# Photo Mode Implementation Plan

> **For agentic workers:** kerjakan task berurutan, tiap task: test → implement → verify → commit.
> Branch: `fitur/photo-mode`. Jangan merge sebelum CI hijau + review 1 orang.

**Goal:** Mode capture kedua — opname via foto per segmen rak (default untuk warung/toko kecil). Lebih murah dari video (6 foto ±18 MB vs video 75 MB), tanpa tracking (nol ID-pecah), OCR expired lebih akurat (foto tajam vs frame blur).

**Architecture:** Reuse penuh komponen teruji: matcher (CLIP cosine + guided mode), expiry parser, OCR, db, report. Yang TIDAK dipakai: tracking, counter berbasis track, crossing — dalam 1 foto, 1 deteksi = 1 barang, dobel hitung antar-foto dicegah lewat SOP (1 foto = 1 sub-segmen berbatas fisik) + review visual di UI.

**Keputusan desain:**
1. `detector` dan `embedder` **injectable** di `scan_photos()` → test end-to-end pakai fake, tanpa download YOLO/CLIP di CI.
2. Hasil per foto disimpan terpisah dalam response (`per_foto`) supaya UI bisa tampilkan review "foto #3: 5 deteksi" dan user bisa spot dobel/gap antar foto.
3. `scans.tipe = 'foto'` (skema sudah support kolom tipe dari branch accounting — plan ini di-merge SETELAH `fitur/accounting-api`).

---

### Task 1: Agregasi deteksi foto (murni, TDD)

**Files:** Create `stoklens/photo.py`, `tests/test_photo.py`

- [ ] **Step 1: Failing test**

```python
from stoklens.photo import aggregate_detections

def test_hitung_lintas_foto():
    # (foto_idx, product_id|None, score)
    det = [(0, 1, 0.9), (0, 1, 0.8), (0, 2, 0.95), (1, 1, 0.85), (1, None, 0.4)]
    out = aggregate_detections(det)
    assert out[1] == {"qty": 3, "confidence_avg": 0.85, "per_foto": {0: 2, 1: 1}}
    assert out[2]["qty"] == 1
    assert out["unknown"]["qty"] == 1

def test_kosong():
    assert aggregate_detections([]) == {}
```

- [ ] **Step 2: Run** `pytest tests/test_photo.py -v` → FAIL
- [ ] **Step 3: Implement**

```python
"""Photo mode: opname via foto per segmen (tanpa tracking).

1 deteksi dalam 1 foto = 1 barang. Anti-dobel antar foto = SOP
(1 foto = 1 sub-segmen berbatas fisik) + review visual per_foto di UI.
"""
from collections import defaultdict


def aggregate_detections(detections):
    """detections: list (foto_idx, product_id|None, score).

    Return {product_id|'unknown': {qty, confidence_avg, per_foto}}.
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
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat: agregasi deteksi photo mode`

---

### Task 2: `scan_photos()` dengan detector/embedder injectable

**Files:** Modify `stoklens/photo.py`, `tests/test_photo.py`

- [ ] **Step 1: Failing test** (fake detector + fake embedder — CI tidak butuh torch)

```python
import numpy as np
from stoklens import db
from stoklens.photo import scan_photos

class FakeEmbedder:
    def embed_bgr(self, crop):
        # crop merah -> [1,0], crop biru -> [0,1]
        return np.array([1.0, 0.0], dtype=np.float32) if crop[..., 2].mean() > 128 \
            else np.array([0.0, 1.0], dtype=np.float32)

def fake_detector(image_bgr):
    # dua kotak tetap: kiri (merah di fixture), kanan (biru)
    return [(0, 0, 50, 50), (60, 0, 110, 50)]

def _fixture_image():
    img = np.zeros((50, 120, 3), dtype=np.uint8)
    img[:, :50, 2] = 255   # merah (BGR)
    img[:, 60:, 0] = 255   # biru
    return img

def test_scan_photos_end_to_end(tmp_path):
    con = db.connect(":memory:")
    p_merah = db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    p_biru = db.add_product(con, "Biru", 2000, np.array([0, 1], dtype=np.float32))
    sid = scan_photos(con, FakeEmbedder(), [_fixture_image()] * 2,
                      detector=fake_detector, read_expiry=False)
    rows = {r["nama"]: r for r in db.get_report_rows(con, sid)}
    assert rows["Merah"]["qty_terdeteksi"] == 2   # 1 per foto x 2 foto
    assert rows["Biru"]["qty_terdeteksi"] == 2
    assert db.get_scan(con, sid)["tipe"] == "foto"
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** — tambah ke `photo.py`:

```python
def _yolo_detector(model_path="yolo11n.pt"):
    from ultralytics import YOLO
    model = YOLO(model_path)

    def detect(image_bgr):
        r = model.predict(image_bgr, verbose=False)[0]
        if r.boxes is None:
            return []
        return [tuple(map(int, b)) for b in r.boxes.xyxy.cpu().numpy()]
    return detect


def scan_photos(con, embedder, images, detector=None, match_threshold=0.75,
                guided_product_id=None, lokasi_rak=None, read_expiry=True):
    """images: list np.ndarray BGR (atau path — dibaca via cv2). Return scan_id."""
    import cv2
    from datetime import date
    from . import db as _db
    from .matcher import match
    from .expiry import parse_expiry

    products = _db.all_products(con)
    allowed = {guided_product_id} if guided_product_id is not None else None
    detect = detector or _yolo_detector()

    detections, crops = [], {}   # crops: (foto_idx, det_idx) -> crop utk OCR
    for i, img in enumerate(images):
        if isinstance(img, (str, bytes)) or hasattr(img, "__fspath__"):
            img = cv2.imread(str(img))
        for j, (x1, y1, x2, y2) in enumerate(detect(img)):
            crop = img[max(y1, 0):y2, max(x1, 0):x2]
            if crop.size == 0:
                continue
            pid, score = match(embedder.embed_bgr(crop), products,
                               threshold=match_threshold, allowed_ids=allowed)
            detections.append((i, pid, score))
            crops[(i, len(detections) - 1)] = (pid, crop)

    counts = aggregate_detections(detections)

    expiry_per_product = {}
    if read_expiry:
        from .ocr import read_text
        for (_, _), (pid, crop) in crops.items():
            if pid is None:
                continue
            d = parse_expiry(read_text(crop))
            if d:
                expiry_per_product.setdefault(pid, []).append(d)

    scan_id = _db.add_scan(con, lokasi_rak=lokasi_rak, tipe="foto")
    today = date.today()
    for pid, c in counts.items():
        if pid == "unknown":
            _db.add_scan_item(con, scan_id, None, c["qty"], c["confidence_avg"])
            continue
        dates = sorted(expiry_per_product.get(pid, []))
        _db.add_scan_item(con, scan_id, pid, c["qty"], c["confidence_avg"],
                          expired_terdekat=dates[0].isoformat() if dates else None,
                          qty_expired=sum(1 for d in dates if d <= today))
    return scan_id
```

- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat: scan_photos dengan detector injectable`

---

### Task 3: Endpoint `POST /api/scans-foto`

**Files:** Modify `stoklens/api.py`, `tests/test_api_ui.py`

- [ ] **Step 1: Failing test** — `create_app(db_path, embedder=..., photo_detector=...)` terima fake dari test; upload 2 foto fixture (encode via `cv2.imencode`), assert report qty & `tipe == "foto"`.
- [ ] **Step 2: Implement** — parameter `photo_detector=None` di `create_app`; endpoint:

```python
@app.post("/api/scans-foto")
async def api_scan_foto(fotos: list[UploadFile], lokasi_rak: str = Form(None),
                        guided_product_id: int = Form(None)):
    import cv2, numpy as np
    from .photo import scan_photos
    images = [cv2.imdecode(np.frombuffer(await f.read(), np.uint8),
                           cv2.IMREAD_COLOR) for f in fotos]
    c = con()
    sid = scan_photos(c, get_embedder(), images, detector=photo_detector,
                      guided_product_id=guided_product_id, lokasi_rak=lokasi_rak)
    return {"scan_id": sid, "report": build_report(db.get_report_rows(c, sid))}
```

- [ ] **Step 3: Run seluruh suite** → PASS. **Step 4: Commit** `feat: endpoint opname via foto`

---

### Task 4: CLI + dokumentasi

**Files:** Modify `scripts/demo_scan.py`, `README.md`, `docs/CATATAN-TIM.md`

- [ ] Subcommand `scan-foto --foto a.jpg b.jpg [--guided-product-id N]`
- [ ] README: alur demo foto; CATATAN-TIM: tambah baris endpoint di tabel kontrak API + section singkat "Mode foto vs video" (kapan pakai yang mana + SOP anti-dobel antar foto: 1 foto = 1 sub-segmen berbatas tiang rak, jangan overlap)
- [ ] Commit `feat: CLI scan-foto + dokumentasi mode foto`

---

### Task 5 (manual, di luar CI): uji lapangan

- [ ] Enroll 3–5 barang dapur → foto 2–3 sub-segmen rak → `scan-foto` → bandingkan hitungan vs manual; catat di sheet uji.

## Urutan merge

1. PR `fitur/accounting-api` merge dulu (photo mode pakai `scans.tipe` dari sana).
2. Rebase `fitur/photo-mode` ke main terbaru → PR → CI hijau → merge.
