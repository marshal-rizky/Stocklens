"""Penyimpanan file crop item tak dikenali, untuk di-review & di-enroll user.

Crop disimpan sebagai file JPEG (path dicatat di `unknown_crops.crop_path`),
BUKAN di DB langsung — hindari BLOB besar di SQLite dan biar bisa disajikan
langsung lewat static file server (Unit 3 me-mount DIR_CROPS_DEFAULT).
"""
import uuid
from pathlib import Path

import cv2

from . import db

# Dipakai bareng Unit 3 (mount StaticFiles) supaya literal direktori cuma
# ditulis di satu tempat.
DIR_CROPS_DEFAULT = Path("data/crops")


def simpan_crop(crop_bgr, scan_id, dir_dasar=None) -> str:
    """Tulis satu crop (numpy BGR) sebagai JPEG, return path-nya (str).

    Folder dikelompokkan per scan (`dir_dasar/<scan_id>/`) supaya crop satu
    scan gampang ditemukan & dibersihkan bareng. Nama file pakai UUID acak
    supaya tidak tabrakan walau banyak crop tersimpan dalam satu scan.

    Path dikembalikan dalam bentuk POSIX (pemisah `/`) — nilai ini masuk ke
    `unknown_crops.crop_path` dan dipakai Unit 3 untuk menyusun URL
    (`/crops/<scan_id>/<file>.jpg`). Tanpa ini, di Windows path berisi
    backslash dan URL yang terbentuk rusak.
    """
    folder = Path(dir_dasar or DIR_CROPS_DEFAULT) / str(scan_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.jpg"
    # cv2.imwrite return False (bukan exception) kalau path/format bermasalah —
    # kalau dibiarkan, unknown_crops.crop_path bakal mengarah ke file yang
    # sebenarnya tidak pernah tertulis.
    if not cv2.imwrite(str(path), crop_bgr):
        raise IOError(f"Gagal menulis crop ke {path}")
    return path.as_posix()


def simpan_buffer(con, scan_id, buffer, dir_dasar=None) -> int:
    """Tulis semua (crop, embedding) di buffer ke disk + tabel `unknown_crops`.

    buffer: iterable (crop_bgr, embedding). Return jumlah yang BERHASIL simpan.

    Kegagalan simpan crop sengaja NON-FATAL. Pemanggil sudah terlanjur commit
    baris `scans` tapi BELUM menulis `scan_items`; kalau exception dibiarkan
    naik (disk penuh, permission, file kekunci antivirus di Windows), user
    kehilangan SELURUH hasil opname — video decode + tracking + CLIP + OCR —
    dan menyisakan baris scan yatim yang bikin laporan kosong senyap.
    Crop unknown cuma bonus untuk fitur enrollment: lebih baik kehilangan satu
    crop daripada seluruh opname.
    """
    tersimpan = 0
    for crop, embedding in buffer:
        try:
            path = simpan_crop(crop, scan_id, dir_dasar)
            db.add_unknown_crop(con, scan_id, path, embedding)
        except OSError:
            continue
        tersimpan += 1
    return tersimpan
