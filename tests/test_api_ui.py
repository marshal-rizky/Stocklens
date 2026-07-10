import numpy as np
from fastapi.testclient import TestClient

from stoklens import db
from stoklens.api import create_app


def _client(tmp_path):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    p1 = db.add_product(con, "Indomie", 3200, np.zeros(4, dtype=np.float32),
                        harga_jual=3500)
    db.update_product(con, p1, stok_minimum=10)
    db.set_stock(con, p1, 40)
    con.close()
    return TestClient(create_app(db_path=dbp)), p1


def test_list_products(tmp_path):
    client, p1 = _client(tmp_path)
    rows = client.get("/api/products").json()
    assert rows[0]["id"] == p1
    assert rows[0]["qty"] == 40
    assert rows[0]["margin_pct"] == 9.4
    assert "embedding" not in rows[0]


def test_product_detail_dengan_ledger(tmp_path):
    client, p1 = _client(tmp_path)
    d = client.get(f"/api/products/{p1}").json()
    assert d["nama"] == "Indomie"
    assert len(d["ledger"]) == 1
    assert d["ledger"][0]["qty_tercatat"] == 40


def test_patch_product(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.patch(f"/api/products/{p1}", json={"harga_jual": 3600})
    assert r.status_code == 200
    assert client.get(f"/api/products/{p1}").json()["harga_jual"] == 3600


def test_patch_field_terlarang_ditolak(tmp_path):
    client, p1 = _client(tmp_path)
    assert client.patch(f"/api/products/{p1}", json={"embedding": "x"}).status_code == 422


def test_adjustment_masuk_ledger(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/adjustments",
                    json={"product_id": p1, "delta": -3, "alasan": "rusak"})
    assert r.status_code == 200
    assert r.json()["qty_baru"] == 37
    ledger = client.get(f"/api/products/{p1}").json()["ledger"]
    assert ledger[0]["alasan"] == "rusak"


def test_adjustment_negatif_ditolak(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/adjustments",
                    json={"product_id": p1, "delta": -100, "alasan": "hilang"})
    assert r.status_code == 400


def test_opname_manual_bikin_laporan(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/opname-manual", json={
        "lokasi_rak": "Rak 1",
        "items": [{"product_id": p1, "qty_fisik": 37}],
    })
    rep = r.json()["report"]
    assert rep["items"][0]["selisih"] == -3
    assert rep["total_shrinkage_rp"] == 9600
    # default: tidak diterapkan ke ledger
    assert client.get(f"/api/products/{p1}").json()["qty"] == 40


def test_opname_manual_terapkan(tmp_path):
    client, p1 = _client(tmp_path)
    client.post("/api/opname-manual", json={
        "lokasi_rak": "Rak 1", "terapkan": True,
        "items": [{"product_id": p1, "qty_fisik": 37}],
    })
    assert client.get(f"/api/products/{p1}").json()["qty"] == 37


def test_dashboard_kpi(tmp_path):
    client, p1 = _client(tmp_path)
    d = client.get("/api/dashboard").json()
    assert d["nilai_stok_rp"] == 40 * 3200
    assert d["potensi_laba_rp"] == 40 * 300
    assert d["scan_terakhir"] is None


def test_export_stok_csv(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.get("/api/export/stok.csv")
    assert r.status_code == 200
    assert "Indomie" in r.text and "3200" in r.text
