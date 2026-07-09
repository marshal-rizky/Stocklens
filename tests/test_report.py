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
                   "total_shrinkage_rp": 0, "total_rugi_expired_rp": 0}
