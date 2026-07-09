"""Wrapper EasyOCR (lazy singleton — load sekali, dipakai berulang)."""
_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["id", "en"], gpu=False, verbose=False)
    return _reader


def read_text(bgr) -> str:
    """Gabungkan semua teks terdeteksi pada crop (BGR numpy array)."""
    return " ".join(get_reader().readtext(bgr, detail=0))
