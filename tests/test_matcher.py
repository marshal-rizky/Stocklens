import numpy as np

from stoklens.matcher import cosine, majority_label, match


def _prods():
    return [
        {"id": 1, "embedding": np.array([1.0, 0.0], dtype=np.float32)},
        {"id": 2, "embedding": np.array([0.0, 1.0], dtype=np.float32)},
    ]


def test_cosine_identik():
    v = np.array([0.6, 0.8], dtype=np.float32)
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_match_pilih_terdekat():
    pid, score = match(np.array([0.9, 0.1], dtype=np.float32), _prods(), threshold=0.5)
    assert pid == 1 and score > 0.5


def test_match_di_bawah_threshold_none():
    pid, _ = match(np.array([0.7, 0.7], dtype=np.float32), _prods(), threshold=0.99)
    assert pid is None


def test_match_guided_mode_batasi_kandidat():
    pid, _ = match(np.array([0.9, 0.1], dtype=np.float32), _prods(),
                   threshold=0.0, allowed_ids={2})
    assert pid == 2


def test_match_skip_embedding_beda_dimensi():
    prods = _prods() + [{"id": 3, "embedding": np.ones(8, dtype=np.float32)}]
    pid, _ = match(np.array([0.9, 0.1], dtype=np.float32), prods, threshold=0.5)
    assert pid == 1  # produk dim-8 di-skip tanpa error


def test_majority_label():
    assert majority_label([1, 1, 2, None, 1]) == 1


def test_majority_label_semua_none():
    assert majority_label([None, None]) is None
