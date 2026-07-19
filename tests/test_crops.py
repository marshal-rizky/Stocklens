import cv2
import numpy as np
import pytest

from stoklens import crops as crops_mod
from stoklens import db
from stoklens.crops import simpan_crop


def _crop(warna=(0, 0, 255)):
    img = np.zeros((20, 30, 3), dtype=np.uint8)
    img[:, :] = warna
    return img


def test_simpan_crop_membuat_file(tmp_path):
    path = simpan_crop(_crop(), scan_id=1, dir_dasar=str(tmp_path / "crops"))
    assert (tmp_path / "crops").exists()
    from pathlib import Path
    assert Path(path).exists()


def test_simpan_crop_bisa_dibaca_balik_dengan_shape_sama(tmp_path):
    crop = _crop((255, 0, 0))
    path = simpan_crop(crop, scan_id=1, dir_dasar=str(tmp_path / "crops"))
    balik = cv2.imread(path)
    assert balik is not None
    assert balik.shape == crop.shape


def test_simpan_crop_dua_kali_scan_sama_beda_path(tmp_path):
    p1 = simpan_crop(_crop(), scan_id=5, dir_dasar=str(tmp_path / "crops"))
    p2 = simpan_crop(_crop(), scan_id=5, dir_dasar=str(tmp_path / "crops"))
    assert p1 != p2


def test_simpan_crop_scan_id_tercermin_di_path(tmp_path):
    path = simpan_crop(_crop(), scan_id=7, dir_dasar=str(tmp_path / "crops"))
    assert "7" in path


def test_simpan_crop_imwrite_gagal_lempar_error_jelas(tmp_path, monkeypatch):
    # cv2.imwrite gagal DIAM-DIAM (return False, bukan exception) — kalau tidak
    # dijaga, unknown_crops.crop_path akan menunjuk file yang tidak pernah ada.
    monkeypatch.setattr(crops_mod.cv2, "imwrite", lambda *a, **kw: False)
    with pytest.raises(IOError, match="Gagal menulis crop"):
        simpan_crop(_crop(), scan_id=1, dir_dasar=str(tmp_path / "crops"))


def test_simpan_crop_path_pakai_garis_miring_bukan_backslash(tmp_path):
    # crop_path dipakai Unit 3 untuk menyusun URL /crops/<scan>/<file>.jpg;
    # di Windows str(Path) menghasilkan backslash dan bikin URL rusak.
    path = simpan_crop(_crop(), scan_id=7, dir_dasar=str(tmp_path / "crops"))
    assert "\\" not in path
    assert path.endswith(".jpg")
    assert "/7/" in path


# ---- simpan_buffer: kegagalan crop harus non-fatal ----

def test_simpan_buffer_lewati_crop_yang_gagal_tanpa_melempar(tmp_path, monkeypatch):
    con = db.connect(":memory:")
    sid = db.add_scan(con)
    buffer = [(_crop(), np.array([1.0, 0.0], dtype=np.float32)),
              (_crop(), np.array([0.0, 1.0], dtype=np.float32))]

    monkeypatch.setattr(crops_mod.cv2, "imwrite",
                        lambda *a, **kw: (_ for _ in ()).throw(OSError("disk penuh")))

    # tidak boleh melempar — pemanggil sudah commit baris scans
    assert crops_mod.simpan_buffer(con, sid, buffer, dir_dasar=tmp_path) == 0
    assert db.list_unknown_crops(con, sid) == []


def test_simpan_buffer_kembalikan_jumlah_yang_berhasil(tmp_path):
    con = db.connect(":memory:")
    sid = db.add_scan(con)
    buffer = [(_crop(), np.array([1.0, 0.0], dtype=np.float32)),
              (_crop(), np.array([0.0, 1.0], dtype=np.float32))]
    assert crops_mod.simpan_buffer(con, sid, buffer, dir_dasar=tmp_path) == 2
    assert len(db.list_unknown_crops(con, sid)) == 2
