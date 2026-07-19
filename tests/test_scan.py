"""Test run_scan() tanpa dependensi torch/ultralytics — model.track() dipalsu
lewat sys.modules["ultralytics"], supaya CI tidak perlu install YOLO/CLIP.
"""
import sys
import types

import cv2
import numpy as np

from stoklens import crops as crops_mod
from stoklens import db, scan


class FakeEmbedder:
    def embed_bgr(self, crop):
        # embedding = luas crop -> beda ukuran box menghasilkan embedding
        # beda. Dipakai untuk membuktikan embedding unknown yang disimpan
        # benar-benar dihitung ulang dari best_crop (crop terbesar), BUKAN
        # dari embs[tid] (sampel embedding antar-frame yang tidak
        # berkorespondensi dengan crop yang ditulis ke disk).
        luas = float(crop.shape[0] * crop.shape[1])
        return np.array([luas, 0.0], dtype=np.float32)


class _Tensor:
    """Tiruan minimal tensor torch: cukup buat .cpu()/.numpy()/.int()/.tolist()."""

    def __init__(self, arr):
        self._arr = np.asarray(arr)

    def cpu(self):
        return self

    def numpy(self):
        return self._arr.astype(np.float32)

    def int(self):
        return _Tensor(self._arr.astype(int))

    def tolist(self):
        return self._arr.tolist()


class _FakeBoxes:
    def __init__(self, xyxy, ids):
        self.xyxy = _Tensor(xyxy)
        self.id = _Tensor(ids) if ids is not None else None


class _FakeResult:
    def __init__(self, orig_img, boxes):
        self.orig_img = orig_img
        self.boxes = boxes


def _pasang_fake_yolo(monkeypatch, frames):
    """Ganti `from ultralytics import YOLO` dengan model palsu yang
    men-track() dari daftar `frames` (list _FakeResult) apa adanya."""
    class _FakeModel:
        def __init__(self, *a, **kw):
            pass

        def track(self, source, stream, persist, verbose, tracker):
            yield from frames

    fake_module = types.SimpleNamespace(YOLO=lambda *a, **kw: _FakeModel())
    monkeypatch.setitem(sys.modules, "ultralytics", fake_module)


def _frame(shape, boxes, ids):
    img = np.zeros(shape, dtype=np.uint8)
    return _FakeResult(img, _FakeBoxes(boxes, ids))


def test_run_scan_unknown_track_embedding_dari_best_crop_bukan_sample(monkeypatch, tmp_path):
    # 1 track (tid=1), 3 frame: kotak makin besar tiap frame.
    # embed_every default=5 -> hanya frame pertama (seen==1) yang di-sample,
    # jadi embs[tid] cuma berisi embedding kotak KECIL (area 100).
    # best_crop harus berupa kotak TERBESAR (area 400, frame ke-3).
    frames = [
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),   # area 100 (di-sample)
        _frame((30, 30, 3), [(0, 0, 10, 20)], [1]),   # area 200
        _frame((30, 30, 3), [(0, 0, 20, 20)], [1]),   # area 400 (terbesar)
    ]
    _pasang_fake_yolo(monkeypatch, frames)

    con = db.connect(":memory:")
    # tidak ada produk terdaftar -> track ini pasti unknown
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, dir_crops=tmp_path)

    belum = db.list_unknown_crops(con, sid)
    assert len(belum) == 1
    info = db.get_unknown_crop(con, belum[0]["id"])
    # embedding tersimpan = luas crop TERBESAR (400), bukan sample pertama (100)
    assert np.allclose(info["embedding"], [400.0, 0.0])


def test_run_scan_pasangan_crop_dan_embedding_tidak_tertukar(monkeypatch, tmp_path):
    # DUA track unknown dengan ukuran kotak BERBEDA -> embedding berbeda,
    # jadi tukar-pasangan di loop persist benar-benar terdeteksi.
    boxes = [(0, 0, 10, 10), (20, 0, 40, 20)]     # luas 100 dan 400
    frames = [_frame((20, 40, 3), boxes, [0, 1]) for _ in range(3)]
    _pasang_fake_yolo(monkeypatch, frames)

    con = db.connect(":memory:")
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, dir_crops=tmp_path)

    baris = db.list_unknown_crops(con, sid)
    assert len(baris) == 2

    luas_tersimpan = []
    for b in baris:
        info = db.get_unknown_crop(con, b["id"])
        gambar = cv2.imread(info["crop_path"])
        assert gambar is not None
        # embedding baris ini harus embedding dari file crop MILIK BARIS INI
        diharapkan = FakeEmbedder().embed_bgr(gambar)
        assert np.allclose(info["embedding"], diharapkan), (
            f"crop {info['crop_path']} berpasangan dengan embedding "
            f"{info['embedding']} — tertukar"
        )
        luas_tersimpan.append(float(diharapkan[0]))

    assert sorted(luas_tersimpan) == [100.0, 400.0]


def test_run_scan_track_pendek_di_bawah_min_track_frames_tidak_disimpan(monkeypatch, tmp_path):
    # track cuma muncul 2 frame, di bawah default min_track_frames=3 ->
    # dibuang oleh aggregate() dan TIDAK boleh ikut disimpan sebagai unknown.
    frames = [
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),
    ]
    _pasang_fake_yolo(monkeypatch, frames)

    con = db.connect(":memory:")
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, dir_crops=tmp_path)
    assert db.list_unknown_crops(con, sid) == []


def test_run_scan_simpan_unknown_bisa_dimatikan(monkeypatch, tmp_path):
    frames = [
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),
        _frame((30, 30, 3), [(0, 0, 10, 10)], [1]),
    ]
    _pasang_fake_yolo(monkeypatch, frames)

    con = db.connect(":memory:")
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, simpan_unknown=False, dir_crops=tmp_path)
    assert db.list_unknown_crops(con, sid) == []


def test_run_scan_gagal_simpan_crop_tidak_membatalkan_opname(monkeypatch, tmp_path):
    """Sama seperti pipeline foto: kegagalan tulis crop tidak boleh
    menghanguskan hasil opname (di video jauh lebih mahal — decode + tracking)."""
    frames = [_frame((30, 30, 3), [(0, 0, 10, 10)], [1]) for _ in range(3)]
    _pasang_fake_yolo(monkeypatch, frames)

    def imwrite_gagal(*a, **kw):
        raise OSError("disk penuh")

    monkeypatch.setattr(crops_mod.cv2, "imwrite", imwrite_gagal)

    con = db.connect(":memory:")
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, dir_crops=tmp_path)

    item_unknown = con.execute(
        "SELECT qty_terdeteksi FROM scan_items WHERE scan_id=? AND product_id IS NULL",
        (sid,),
    ).fetchone()
    assert item_unknown["qty_terdeteksi"] == 1    # opname tetap tercatat
    assert db.list_unknown_crops(con, sid) == []  # cuma crop bonus yang hilang


def test_run_scan_batas_maks_unknown_per_scan(monkeypatch, tmp_path):
    # 5 track berbeda, semua muncul bersamaan 3 frame -> semua lolos
    # min_track_frames dan semua unknown (tidak ada produk terdaftar).
    boxes = [(x, 0, x + 5, 5) for x in range(0, 50, 10)]   # 5 kotak non-overlap
    ids = [0, 1, 2, 3, 4]
    frames = [_frame((5, 50, 3), boxes, ids) for _ in range(3)]
    _pasang_fake_yolo(monkeypatch, frames)

    con = db.connect(":memory:")
    sid = scan.run_scan(con, FakeEmbedder(), "fake.mp4", count_mode="track",
                        read_expiry=False, maks_unknown=2, dir_crops=tmp_path)

    assert len(db.list_unknown_crops(con, sid)) == 2   # dibatasi cap
    row = con.execute(
        "SELECT qty_terdeteksi FROM scan_items WHERE scan_id=? AND product_id IS NULL",
        (sid,),
    ).fetchone()
    assert row["qty_terdeteksi"] == 5   # hitungan report TIDAK ikut dibatasi
