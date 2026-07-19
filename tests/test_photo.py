import cv2
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


# ---- simpan crop unknown (Unit 2) ----

def test_scan_photos_simpan_unknown_crop_embedding_sesuai_crop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)   # data/crops relatif ke tmp_path, bukan repo
    con = db.connect(":memory:")
    db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    # "Biru" sengaja tidak didaftarkan -> crop kanan jadi unknown
    sid = scan_photos(con, FakeEmbedder(), [_fixture_image()],
                      detector=fake_detector, read_expiry=False)

    belum = db.list_unknown_crops(con, sid)
    assert len(belum) == 1

    info = db.get_unknown_crop(con, belum[0]["id"])
    tersimpan = cv2.imread(info["crop_path"])
    assert tersimpan is not None
    # embedding tersimpan harus persis embedding dari crop yang ditulis ke
    # disk (bukan crop lain) — syarat wajib supaya galeri produk (Unit 3)
    # tidak tercemar saat user meng-assign crop ini.
    assert np.allclose(info["embedding"], FakeEmbedder().embed_bgr(tersimpan))


class AreaEmbedder:
    """Embedding = luas crop, jadi tiap crop berukuran beda punya embedding
    yang beda dan bisa dilacak balik dari file gambarnya sendiri.

    FakeEmbedder biasa cuma punya 2 nilai keluaran (merah/bukan merah),
    terlalu tumpul untuk membuktikan pasangan crop<->embedding benar.
    """

    def embed_bgr(self, crop):
        return np.array([float(crop.shape[0] * crop.shape[1]), 0.0],
                        dtype=np.float32)


def test_scan_photos_pasangan_crop_dan_embedding_tidak_tertukar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    con = db.connect(":memory:")
    # tidak ada produk terdaftar -> kedua deteksi jadi unknown

    def detector_dua_ukuran(image_bgr):
        # dua kotak dengan LUAS BERBEDA -> embedding berbeda & bisa dibedakan
        return [(0, 0, 10, 10), (20, 0, 40, 20)]      # luas 100 dan 400

    img = np.zeros((20, 40, 3), dtype=np.uint8)
    sid = scan_photos(con, AreaEmbedder(), [img], detector=detector_dua_ukuran,
                      read_expiry=False)

    baris = db.list_unknown_crops(con, sid)
    assert len(baris) == 2

    luas_tersimpan = []
    for b in baris:
        info = db.get_unknown_crop(con, b["id"])
        gambar = cv2.imread(info["crop_path"])
        assert gambar is not None
        # Inti test: embedding yang tercatat di baris ini harus embedding dari
        # file crop MILIK BARIS INI juga. Kalau loop persist menukar pasangan
        # (crop A dapat embedding B), assert ini gagal.
        diharapkan = AreaEmbedder().embed_bgr(gambar)
        assert np.allclose(info["embedding"], diharapkan), (
            f"crop {info['crop_path']} (luas {gambar.shape[0] * gambar.shape[1]}) "
            f"berpasangan dengan embedding {info['embedding']} — tertukar"
        )
        luas_tersimpan.append(float(diharapkan[0]))

    # pastikan kedua crop memang beda ukuran, jadi tukar-pasangan benar-benar
    # terdeteksi (kalau luasnya sama, test ini tidak membuktikan apa-apa)
    assert sorted(luas_tersimpan) == [100.0, 400.0]


def test_scan_photos_simpan_unknown_bisa_dimatikan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    con = db.connect(":memory:")
    db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    sid = scan_photos(con, FakeEmbedder(), [_fixture_image()],
                      detector=fake_detector, read_expiry=False,
                      simpan_unknown=False)
    assert db.list_unknown_crops(con, sid) == []


def test_scan_photos_batas_maks_unknown_per_scan(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    con = db.connect(":memory:")
    # tidak ada produk terdaftar sama sekali -> semua deteksi unknown

    def detector_banyak(image_bgr):
        # 10 kotak kecil non-overlap dalam satu foto
        return [(x, 0, x + 5, 5) for x in range(0, 100, 10)]

    img = np.zeros((5, 100, 3), dtype=np.uint8)
    sid = scan_photos(con, FakeEmbedder(), [img], detector=detector_banyak,
                      read_expiry=False, maks_unknown=3)

    assert len(db.list_unknown_crops(con, sid)) == 3   # dibatasi cap
    row = con.execute(
        "SELECT qty_terdeteksi FROM scan_items WHERE scan_id=? AND product_id IS NULL",
        (sid,),
    ).fetchone()
    assert row["qty_terdeteksi"] == 10   # hitungan report TIDAK ikut dibatasi
