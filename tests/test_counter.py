from stoklens.counter import TrackResult, aggregate


def test_hitung_per_produk():
    tracks = [
        TrackResult(1, 10, 0.9, 12),
        TrackResult(2, 10, 0.8, 8),
        TrackResult(3, 20, 0.95, 5),
    ]
    out = aggregate(tracks)
    assert out[10]["qty"] == 2
    assert out[10]["confidence_avg"] == 0.85
    assert out[20]["qty"] == 1


def test_track_pendek_dibuang():
    out = aggregate([TrackResult(1, 10, 0.9, 2)], min_track_frames=3)
    assert out == {}


def test_tanpa_label_masuk_unknown():
    out = aggregate([TrackResult(1, None, 0.4, 10)])
    assert out["unknown"]["qty"] == 1
