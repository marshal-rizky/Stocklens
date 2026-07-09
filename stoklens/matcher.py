"""Pencocokan embedding crop ke galeri produk (brute-force cosine)."""
from collections import Counter

import numpy as np


def cosine(a, b) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def match(embedding, products, threshold=0.75, allowed_ids=None):
    """Return (product_id, score); product_id None kalau di bawah threshold.

    allowed_ids: batasi kandidat (guided mode / deklarasi produk per blok).
    """
    best_id, best_score = None, -1.0
    for p in products:
        if allowed_ids is not None and p["id"] not in allowed_ids:
            continue
        s = cosine(embedding, p["embedding"])
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
