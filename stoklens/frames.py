"""Iterasi frame video dengan sampling tetap."""
import cv2


def iter_frames(video_path, every_n=15):
    """Yield (frame_index, frame_bgr) tiap `every_n` frame."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Video tidak bisa dibuka: {video_path}")
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % every_n == 0:
                yield idx, frame
            idx += 1
    finally:
        cap.release()
