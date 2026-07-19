"""Pencocokan embedding crop ke galeri produk (brute-force cosine)."""
from collections import Counter

import numpy as np


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def match(embedding, products, threshold=0.75, allowed_ids=None):
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
        galeri = p["embeddings"] if "embeddings" in p else [p["embedding"]]
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
