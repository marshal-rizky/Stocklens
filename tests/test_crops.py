import cv2
import numpy as np

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
