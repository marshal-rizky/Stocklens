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


def _tahun(t: str) -> int:
    n = int(t)
    return n + 2000 if n < 100 else n


def parse_expiry(text: str) -> date | None:
    """Ambil tanggal expired pertama yang valid; None kalau tidak ketemu.

    Format bulan-tahun dipetakan ke tanggal 1 bulan tersebut.
    """
    if not text:
        return None
    t = text.upper()
    m = _KEYWORD.search(t)
    if m:
        t = t[m.end():]
    dmy = _DMY.search(t)
    if dmy:
        d, mo, y = int(dmy[1]), int(dmy[2]), _tahun(dmy[3])
        if 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return date(y, mo, d)
            except ValueError:
                return None
    mon = _MON_Y.search(t)
    if mon and mon[1][:3] in BULAN:
        return date(_tahun(mon[2]), BULAN[mon[1][:3]], 1)
    my = _MY.search(t)
    if my:
        mo, y = int(my[1]), _tahun(my[2])
        if 1 <= mo <= 12 and 2000 <= y <= 2100:
            return date(y, mo, 1)
    return None
