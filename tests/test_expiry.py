from datetime import date

from stoklens.expiry import parse_expiry


def test_bulan_tahun_numerik():
    assert parse_expiry("EXP 03 2027") == date(2027, 3, 1)


def test_tanggal_lengkap_slash_tahun_pendek():
    assert parse_expiry("ED 12/08/26") == date(2026, 8, 12)


def test_nama_bulan_indonesia():
    assert parse_expiry("BAIK SEBELUM: AGU 2026") == date(2026, 8, 1)


def test_bulan_titik():
    assert parse_expiry("EXP: 03.27") == date(2027, 3, 1)


def test_tanpa_tanggal():
    assert parse_expiry("INDOMIE GORENG 85G") is None


def test_teks_kosong():
    assert parse_expiry("") is None
