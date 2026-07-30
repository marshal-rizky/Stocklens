"""Parser tanggal expired dari teks OCR kemasan (format umum Indonesia)."""
import re
from datetime import date

BULAN = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MEI": 5, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGU": 8, "AGT": 8, "AUG": 8, "SEP": 9, "OKT": 10, "OCT": 10,
    "NOV": 11, "DES": 12, "DEC": 12,
}

_KEYWORD = re.compile(r"(?:EXP(?:IRED)?|ED|BB|BAIK\s*SEBELUM|BEST\s*BEFORE)\s*[:.]?\s*", re.I)
_DMY = re.compile(r"\b(\d{1,2})[\s/.\-](\d{1,2})[\s/.\-](\d{2,4})\b")
_MON_Y = re.compile(r"\b([A-Z]{3})[A-Z]*[\s/.\-]?(\d{2,4})\b")
_MY = re.compile(r"\b(\d{1,2})[\s/.\-](\d{2,4})\b")

# Jendela tanggal yang dianggap masuk akal untuk barang di rak warung.
# Di luar jendela ini, salah-baca OCR jauh lebih mungkin daripada tanggal nyata.
TAHUN_TOLERANSI_LALU = 2
TAHUN_TOLERANSI_DEPAN = 10


def _tahun(t: str) -> int:
    n = int(t)
    return n + 2000 if n < 100 else n


def _masuk_jendela(d: date, hari_ini: date) -> bool:
    """Buang tanggal yang hampir pasti salah-baca.

    Barang yang kedaluwarsa 3+ tahun lalu dalam jumlah banyak jauh lebih mungkin
    hasil OCR yang keliru (kode batch, nomor izin edar) daripada stok nyata —
    dan melaporkannya sebagai "rugi expired" berarti menyodorkan angka rupiah
    palsu ke pemilik warung.
    """
    return (
        date(hari_ini.year - TAHUN_TOLERANSI_LALU, hari_ini.month, 1)
        <= d
        <= date(hari_ini.year + TAHUN_TOLERANSI_DEPAN, 12, 31)
    )


def parse_expiry(text: str, hari_ini: date | None = None) -> date | None:
    """Ambil tanggal expired pertama yang valid; None kalau tidak ketemu.

    Format bulan-tahun dipetakan ke tanggal 1 bulan tersebut.

    DUA ATURAN KETAT — jangan dilonggarkan tanpa mengukur ulang di lapangan:

    1. **Pola angka polos (`DD MM YY`, `MM YY`) hanya diterima kalau ada kata
       kunci** (`EXP`, `ED`, `BB`, `BAIK SEBELUM`, `BEST BEFORE`). Tanpa aturan
       ini, kode batch di kemasan terbaca sebagai tanggal: `LOT 12 05 23 PROD`
       dulu menghasilkan 2023-05-12, lalu dihitung sebagai rugi expired.
       Pola dengan nama bulan huruf (`AGU 27`) tetap diterima tanpa kata kunci —
       huruf bulan sinyal kuat yang tidak muncul di kode batch numerik.

    2. **Tanggal di luar jendela wajar ditolak** (lihat `_masuk_jendela`).

    hari_ini: hanya untuk test; default tanggal hari ini.
    """
    if not text:
        return None
    hari_ini = hari_ini or date.today()
    t = text.upper()

    m = _KEYWORD.search(t)
    ada_kunci = m is not None
    if ada_kunci:
        t = t[m.end():]

    kandidat = None

    # Pola angka polos: hanya dipercaya kalau didahului kata kunci.
    if ada_kunci:
        dmy = _DMY.search(t)
        if dmy:
            d, mo, y = int(dmy[1]), int(dmy[2]), _tahun(dmy[3])
            if 1 <= mo <= 12 and 1 <= d <= 31:
                try:
                    kandidat = date(y, mo, d)
                except ValueError:
                    return None

    if kandidat is None:
        mon = _MON_Y.search(t)
        if mon and mon[1][:3] in BULAN:
            kandidat = date(_tahun(mon[2]), BULAN[mon[1][:3]], 1)

    if kandidat is None and ada_kunci:
        my = _MY.search(t)
        if my:
            mo, y = int(my[1]), _tahun(my[2])
            if 1 <= mo <= 12 and 2000 <= y <= 2100:
                kandidat = date(y, mo, 1)

    if kandidat is None or not _masuk_jendela(kandidat, hari_ini):
        return None
    return kandidat
