from stoklens.report import build_report


def test_selisih_dan_rupiah():
    rows = [{"nama": "Indomie", "harga_modal": 3200, "qty_tercatat": 40,
             "qty_terdeteksi": 37, "qty_expired": 2}]
    rep = build_report(rows)
    item = rep["items"][0]
    assert item["selisih"] == -3
    assert item["shrinkage_rp"] == 9600
    assert item["rugi_expired_rp"] == 6400
    assert item["nilai_stok_rp"] == 37 * 3200
    assert rep["total_shrinkage_rp"] == 9600


def test_surplus_bukan_shrinkage():
    rows = [{"nama": "Gula", "harga_modal": 12000, "qty_tercatat": 5,
             "qty_terdeteksi": 6, "qty_expired": 0}]
    rep = build_report(rows)
    assert rep["items"][0]["selisih"] == 1
    assert rep["items"][0]["shrinkage_rp"] == 0


def test_report_kosong():
    rep = build_report([])
    assert rep == {"items": [], "total_nilai_rp": 0,
                   "total_shrinkage_rp": 0, "total_rugi_expired_rp": 0,
                   "tidak_terdeteksi": [], "total_tidak_terdeteksi_rp": 0}


# --- barang tak terdeteksi -------------------------------------------------
# Barang berstok yang tidak muncul di scan HARUS terlihat user (kasus paling
# penting: barang habis tanpa tercatat), tapi nilainya TIDAK boleh masuk
# shrinkage otomatis. Alasannya: scan satu rak tidak melihat rak lain, jadi
# menghitungnya otomatis melaporkan seluruh barang rak lain sebagai hilang.

def test_tidak_terdeteksi_tampil_tapi_tidak_menambah_shrinkage():
    rows = [{"nama": "Indomie", "harga_modal": 3200, "qty_tercatat": 40,
             "qty_terdeteksi": 38, "qty_expired": 0}]
    hilang = [{"id": 2, "nama": "Yakult", "harga_modal": 2000,
               "qty_tercatat": 20, "nilai_rp": 40000}]
    rep = build_report(rows, tidak_terdeteksi=hilang)

    assert [i["nama"] for i in rep["tidak_terdeteksi"]] == ["Yakult"]
    assert rep["total_tidak_terdeteksi_rp"] == 40000
    # shrinkage tetap HANYA dari selisih Indomie (2 x 3200)
    assert rep["total_shrinkage_rp"] == 6400
    # dan tidak menyusup ke daftar item biasa
    assert [i["nama"] for i in rep["items"]] == ["Indomie"]


def test_tidak_terdeteksi_default_kosong():
    """Pemanggil lama yang tidak mengoper argumen ini tetap jalan."""
    rep = build_report([{"nama": "A", "harga_modal": 100, "qty_tercatat": 1,
                         "qty_terdeteksi": 1, "qty_expired": 0}])
    assert rep["tidak_terdeteksi"] == []
    assert rep["total_tidak_terdeteksi_rp"] == 0


def test_ambang_bawaan_satu_sumber():
    """Ambang tidak boleh berbeda antara matcher, foto, dan video.

    Sebelumnya angkanya ditulis tiga kali. Kalau salah satu diubah dan yang lain
    tidak, opname foto dan opname video memakai keketatan berbeda tanpa ada yang
    gagal — dan hasilnya cuma terlihat sebagai "kadang beda". Nilainya sendiri
    diukur, lihat docs/HASIL-UJI-AMBANG-CLIP.md.
    """
    import inspect

    from stoklens import photo, scan
    from stoklens.matcher import AMBANG_BAWAAN, match

    assert AMBANG_BAWAAN == 0.80
    for fn, arg in ((match, "threshold"),
                    (photo.scan_photos, "match_threshold"),
                    (scan.run_scan, "match_threshold")):
        bawaan = inspect.signature(fn).parameters[arg].default
        assert bawaan == AMBANG_BAWAAN, f"{fn.__name__}({arg}) = {bawaan}"
