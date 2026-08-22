"""Wrapper EasyOCR (lazy singleton — load sekali, dipakai berulang).

TIDAK DIPAKAI SECARA BAWAAN sejak 22 Agu 2026. Diukur pada foto warung asli:
OCR menemukan tanggal kedaluwarsa pada 0 dari 64 potongan, resolusi penuh
sekalipun. OCR-nya sendiri bekerja — 43 dari 64 potongan menghasilkan teks
berupa nama merek dan tulisan besar kemasan — tetapi tanggalnya tidak pernah
muncul. Sebabnya struktural: tanggal kedaluwarsa dicetak inkjet atau laser
tipis berkontras rendah di belakang, di bawah, atau pada lipatan sambungan,
sedangkan sisi yang menghadap rak justru sisi yang tidak membawanya. Menaikkan
resolusi tidak menolong karena informasinya memang tidak ada di dalam frame.

Modul ini dipertahankan karena `scan_photos(read_expiry=True)` masih bisa
dinyalakan — jalan yang masuk akal bila diteruskan kelak adalah foto close-up
satu kemasan, bukan foto rak.
"""
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
