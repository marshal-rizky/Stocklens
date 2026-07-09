import numpy as np

from stoklens import db


def _con():
    return db.connect(":memory:")


def test_add_dan_baca_product():
    con = _con()
    emb = np.arange(4, dtype=np.float32)
    pid = db.add_product(con, "Indomie Goreng", 3200, emb, harga_jual=3500)
    rows = db.all_products(con)
    assert len(rows) == 1
    assert rows[0]["id"] == pid
    assert rows[0]["nama"] == "Indomie Goreng"
    assert np.allclose(rows[0]["embedding"], emb)


def test_stock_ledger_ambil_terbaru():
    con = _con()
    pid = db.add_product(con, "Minyak 1L", 15000, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 40)
    db.set_stock(con, pid, 37)
    assert db.get_stock_map(con) == {pid: 37}


def test_scan_dan_report_rows():
    con = _con()
    pid = db.add_product(con, "Gula 1kg", 12000, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 10)
    sid = db.add_scan(con, video_ref="rak1.mp4", lokasi_rak="Rak 1")
    db.add_scan_item(con, sid, pid, qty_terdeteksi=8, confidence_avg=0.91,
                     expired_terdekat="2026-08-01", qty_expired=2)
    rows = db.get_report_rows(con, sid)
    assert rows == [{
        "nama": "Gula 1kg", "harga_modal": 12000, "qty_tercatat": 10,
        "qty_terdeteksi": 8, "qty_expired": 2,
        "expired_terdekat": "2026-08-01", "confidence_avg": 0.91,
    }]
