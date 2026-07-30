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


# --- kode batch bukan tanggal kedaluwarsa (edge case review 2026-07-30) -----
# Sebelumnya parser mencari pola angka di SELURUH teks kalau kata kunci tidak
# ketemu, sehingga kode produksi jadi "tanggal expired" di masa lalu dan
# dihitung sebagai rugi expired. Terverifikasi:
#   'LOT 12 05 23 PROD'         -> 2023-05-12
#   'NETTO 85 g  KODE 10 04 22' -> 2022-04-10
# Akibatnya user melihat "Potensi rugi expired Rp ..." yang seluruhnya fabrikasi.

HARI_INI = date(2026, 7, 30)


def test_kode_batch_tanpa_kata_kunci_diabaikan():
    assert parse_expiry("LOT 12 05 23 PROD", hari_ini=HARI_INI) is None
    assert parse_expiry("NETTO 85 g  KODE 10 04 22", hari_ini=HARI_INI) is None
    assert parse_expiry("5 2050", hari_ini=HARI_INI) is None


def test_nama_bulan_huruf_tetap_diterima_tanpa_kata_kunci():
    """Bulan huruf adalah sinyal kuat — tidak muncul di kode batch numerik."""
    assert parse_expiry("AGU 27", hari_ini=HARI_INI) == date(2027, 8, 1)


def test_pola_angka_diterima_kalau_ada_kata_kunci():
    assert parse_expiry("EXP 12 05 2027", hari_ini=HARI_INI) == date(2027, 5, 12)
    assert parse_expiry("BB 08 26", hari_ini=HARI_INI) == date(2026, 8, 1)


def test_tanggal_terlalu_lama_di_masa_lalu_ditolak():
    """Barang kedaluwarsa 3 tahun lalu dalam jumlah banyak lebih mungkin
    salah-baca daripada nyata."""
    assert parse_expiry("EXP 01 01 2020", hari_ini=HARI_INI) is None
    # masih dalam jendela: baru lewat, wajar dilaporkan
    assert parse_expiry("EXP 01 06 2026", hari_ini=HARI_INI) == date(2026, 6, 1)


def test_tanggal_terlalu_jauh_di_masa_depan_ditolak():
    assert parse_expiry("EXP 01 01 2099", hari_ini=HARI_INI) is None
