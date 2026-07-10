import numpy as np

from stoklens import db
from stoklens.photo import aggregate_detections, scan_photos


def test_hitung_lintas_foto():
    # (foto_idx, product_id|None, score)
    det = [(0, 1, 0.9), (0, 1, 0.8), (0, 2, 0.95), (1, 1, 0.85), (1, None, 0.4)]
    out = aggregate_detections(det)
    assert out[1] == {"qty": 3, "confidence_avg": 0.85, "per_foto": {0: 2, 1: 1}}
    assert out[2]["qty"] == 1
    assert out["unknown"]["qty"] == 1


def test_kosong():
    assert aggregate_detections([]) == {}


# ---- scan_photos end-to-end dengan detector & embedder palsu (tanpa torch) ----

class FakeEmbedder:
    def embed_bgr(self, crop):
        # crop dominan merah -> [1,0]; selain itu -> [0,1]
        if crop[..., 2].mean() > 128:
            return np.array([1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 1.0], dtype=np.float32)


def fake_detector(image_bgr):
    # dua kotak tetap: kiri (merah di fixture), kanan (biru)
    return [(0, 0, 50, 50), (60, 0, 110, 50)]


def _fixture_image():
    img = np.zeros((50, 120, 3), dtype=np.uint8)
    img[:, :50, 2] = 255   # merah (BGR: channel 2 = R)
    img[:, 60:, 0] = 255   # biru
    return img


def test_scan_photos_end_to_end(tmp_path):
    con = db.connect(":memory:")
    db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    db.add_product(con, "Biru", 2000, np.array([0, 1], dtype=np.float32))
    sid = scan_photos(con, FakeEmbedder(), [_fixture_image()] * 2,
                      detector=fake_detector, read_expiry=False)
    rows = {r["nama"]: r for r in db.get_report_rows(con, sid)}
    assert rows["Merah"]["qty_terdeteksi"] == 2   # 1 per foto x 2 foto
    assert rows["Biru"]["qty_terdeteksi"] == 2
    assert db.get_scan(con, sid)["tipe"] == "foto"


def test_scan_photos_guided_mode(tmp_path):
    con = db.connect(":memory:")
    p_merah = db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    db.add_product(con, "Biru", 2000, np.array([0, 1], dtype=np.float32))
    # guided: semua deteksi dipaksa kandidat "Merah" saja
    sid = scan_photos(con, FakeEmbedder(), [_fixture_image()],
                      detector=fake_detector, read_expiry=False,
                      guided_product_id=p_merah, match_threshold=0.0)
    rows = {r["nama"]: r for r in db.get_report_rows(con, sid)}
    assert rows["Merah"]["qty_terdeteksi"] == 2
    assert "Biru" not in rows
