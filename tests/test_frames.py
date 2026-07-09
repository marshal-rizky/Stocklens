import cv2
import numpy as np
import pytest

from stoklens.frames import iter_frames


def _video(tmp_path, n=30):
    p = str(tmp_path / "v.avi")
    w = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for i in range(n):
        w.write(np.full((48, 64, 3), i * 8 % 255, dtype=np.uint8))
    w.release()
    return p


def test_ambil_setiap_n_frame(tmp_path):
    frames = list(iter_frames(_video(tmp_path), every_n=10))
    assert [i for i, _ in frames] == [0, 10, 20]
    assert frames[0][1].shape == (48, 64, 3)


def test_file_tidak_ada():
    with pytest.raises(FileNotFoundError):
        list(iter_frames("tidak_ada.avi"))
