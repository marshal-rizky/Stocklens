"""Penyimpanan file crop item tak dikenali, untuk di-review & di-enroll user.

Crop disimpan sebagai file JPEG (path dicatat di `unknown_crops.crop_path`),
BUKAN di DB langsung — hindari BLOB besar di SQLite dan biar bisa disajikan
langsung lewat static file server (Unit 3).
"""
import uuid
from pathlib import Path

import cv2


def simpan_crop(crop_bgr, scan_id, dir_dasar="data/crops") -> str:
    """Tulis satu crop (numpy BGR) sebagai JPEG, return path-nya (str).

    Folder dikelompokkan per scan (`dir_dasar/<scan_id>/`) supaya crop satu
    scan gampang ditemukan & dibersihkan bareng. Nama file pakai UUID acak
    supaya tidak tabrakan walau banyak crop tersimpan dalam satu scan.
    """
    folder = Path(dir_dasar) / str(scan_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.jpg"
    # cv2.imwrite return False (bukan exception) kalau path/format bermasalah —
    # kalau dibiarkan, unknown_crops.crop_path bakal mengarah ke file yang
    # sebenarnya tidak pernah tertulis.
    if not cv2.imwrite(str(path), crop_bgr):
        raise IOError(f"Gagal menulis crop ke {path}")
    return str(path)
