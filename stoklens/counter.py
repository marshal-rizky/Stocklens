"""Agregasi hasil tracking menjadi hitungan per produk."""
from dataclasses import dataclass


@dataclass
class TrackResult:
    track_id: int
    product_id: int | None
    confidence: float
    n_frames: int


def aggregate(tracks, min_track_frames=3):
    """{product_id | 'unknown': {'qty': int, 'confidence_avg': float}}.

    Track dengan n_frames < min_track_frames dibuang (noise/ID pecah singkat).
    """
    out = {}
    for t in tracks:
        if t.n_frames < min_track_frames:
            continue
        key = t.product_id if t.product_id is not None else "unknown"
        d = out.setdefault(key, {"qty": 0, "_scores": []})
        d["qty"] += 1
        d["_scores"].append(t.confidence)
    for d in out.values():
        d["confidence_avg"] = round(sum(d.pop("_scores")) / d["qty"], 3)
    return out
