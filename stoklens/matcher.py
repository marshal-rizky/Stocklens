"""Pencocokan embedding crop ke galeri produk (brute-force cosine)."""
from collections import Counter

import numpy as np


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# Diukur 3 Agustus 2026 di 12 produk / 104 foto enrollment — lihat
# docs/HASIL-UJI-AMBANG-CLIP.md dan scripts/ukur_ambang_clip.py.
#
# Ambang mengerjakan dua hal yang tarik-menarik. Yang menentukan adalah tugas
# yang sebelumnya tidak pernah diuji: menolak barang yang BELUM di-enroll. Rak
# warung memuat ratusan barang sementara yang didaftarkan cuma puluhan, jadi
# barang asing jauh lebih banyak daripada yang terdaftar.
#
#   ambang   kenali terdaftar   tolak asing
#   0,75     recall 0,933       68,3 %   <- 1 dari 3 barang asing lolos
#   0,80     recall 0,875       84,6 %   <- dipakai sekarang
#   0,85     recall 0,673       100 %    <- lama
#
# Barang asing yang lolos muncul di laporan sebagai barang dengan NAMA SALAH —
# terbaca meyakinkan dan tidak meninggalkan tanda. Barang terdaftar yang ditolak
# cuma jadi "belum dikenali", dan pengguna bisa melihat sendiri bahwa itu ada.
# Salah menyebut lebih mahal daripada tidak menyebut, jadi 0,85 dipilih lebih
# dulu. Yang membatalkan pilihan itu adalah ukuran pertama pada foto rak asli,
# bukan foto enrollment.
#
# Diukur ulang 22 Agustus 2026, satu foto rak berisi 19 botol, 3 di antaranya
# sudah didaftarkan lewat foto close-up:
#
#   Mizone     0,888   dikenali
#   Teh pucuk  0,833   DITOLAK 0,85, padahal benar
#   Mizone #2  0,741   DITOLAK 0,85, padahal benar
#   kandidat salah tertinggi di antara 16 botol asing sisanya:  0,613
#
# Jarak antara 0,613 dan 0,741 itu yang menentukan. Pemisahan produk terdaftar
# dan barang asing masih sehat; yang salah cuma letak ambangnya. Potongan dari
# rak lebarnya 63 sampai 110 piksel, miring, kena pantulan kaca, jadi skornya
# turun sekitar 0,05 sampai 0,11 dibanding foto enrollment yang close-up.
# Ambang 0,85 dikalibrasi pada foto enrollment, dan itu memang batas atas yang
# sudah diperingatkan di catatan sebelumnya.
#
# 0,80 masih di atas 0,613 dengan selisih lebar, dan pada foto uji ini nol salah
# label. Ukur ulang lagi setelah uji lapangan penuh: kalau rak sungguhan
# memunculkan barang asing di atas 0,70, ambang tetap ini perlu diganti ambang
# adaptif per produk.
AMBANG_BAWAAN = 0.80


def match(embedding, products, threshold=AMBANG_BAWAAN, allowed_ids=None):
    """Return (product_id, score); product_id None kalau di bawah threshold.

    Similarity satu produk = tertinggi di antara entri galerinya (`p["embeddings"]`).
    Kalau produk hanya punya `embedding` tunggal (belum ada galeri), itu diperlakukan
    sebagai galeri satu entri. TIDAK dirata-rata — embedding enrollment (foto rapi)
    dan embedding scan (angle/lighting toko) sengaja dipisah, rata-rata bisa jadi
    vektor yang tidak mirip keduanya.

    allowed_ids: batasi kandidat (guided mode / deklarasi produk per blok).
    """
    best_id, best_score = None, -1.0
    for p in products:
        if allowed_ids is not None and p["id"] not in allowed_ids:
            continue
        # Jalur singular = kompat untuk test & pemanggil lama yang belum
        # minta galeri (all_products tanpa with_gallery).
        galeri = p.get("embeddings") or [p["embedding"]]
        for emb in galeri:
            # Entri dengan dimensi embedding beda (data korup/legacy) di-skip,
            # jangan sampai satu baris jelek meledakkan seluruh scan.
            if len(emb) != len(embedding):
                continue
            s = cosine(embedding, emb)
            if s > best_score:
                best_id, best_score = p["id"], s
    if best_score < threshold:
        return None, best_score
    return best_id, best_score


def majority_label(labels):
    """Label mayoritas satu track (abaikan None); None kalau tidak ada suara."""
    votes = [l for l in labels if l is not None]
    if not votes:
        return None
    return Counter(votes).most_common(1)[0][0]


def average_embedding(vecs) -> np.ndarray:
    """Rata-rata beberapa embedding, dinormalisasi ulang (murni numpy —
    sengaja di sini, bukan di embedder.py, supaya enroll.py bebas torch)."""
    m = np.mean(np.stack(vecs), axis=0)
    return (m / (np.linalg.norm(m) + 1e-9)).astype(np.float32)
