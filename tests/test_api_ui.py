import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

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


def test_opname_manual_terapkan_report_pakai_stok_sebelum_terapkan(tmp_path):
    # Kunci urutan: report HARUS dibangun sebelum terapkan ke ledger. Kalau
    # terapkan jalan duluan, qty_tercatat = qty_fisik dan semua selisih jadi 0
    # (laporan sampah, tapi tetap HTTP 200). Jangan disederhanakan jadi cek stok.
    client, p1 = _client(tmp_path)     # stok tercatat awal 40
    rep = client.post("/api/opname-manual", json={
        "lokasi_rak": "Rak 1", "terapkan": True,
        "items": [{"product_id": p1, "qty_fisik": 37}],
    }).json()["report"]
    assert rep["items"][0]["qty_tercatat"] == 40    # stok SEBELUM terapkan
    assert rep["items"][0]["selisih"] == -3
    assert rep["total_shrinkage_rp"] == 9600
    assert client.get(f"/api/products/{p1}").json()["qty"] == 37   # tetap diterapkan


def test_list_scans_urutan_dan_total(tmp_path):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    p1 = db.add_product(con, "Indomie", 3200, np.zeros(4, dtype=np.float32))
    db.set_stock(con, p1, 40)
    sid1 = db.add_scan(con, lokasi_rak="Rak 1", tipe="manual")
    db.add_scan_item(con, sid1, p1, 37)
    sid2 = db.add_scan(con, lokasi_rak="Rak 2", tipe="foto")
    db.add_scan_item(con, sid2, p1, 35)
    con.close()
    client = TestClient(create_app(db_path=dbp))
    rows = client.get("/api/scans").json()
    assert [r["id"] for r in rows] == [sid2, sid1]
    assert rows[0]["total_shrinkage_rp"] == (40 - 35) * 3200
    assert rows[1]["total_shrinkage_rp"] == (40 - 37) * 3200


def test_opname_terapkan(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": p1, "qty_fisik": 33}],
    })
    scan_id = r.json()["scan_id"]
    assert client.get(f"/api/products/{p1}").json()["qty"] == 40  # belum diterapkan

    r2 = client.post(f"/api/opname/{scan_id}/terapkan")
    assert r2.status_code == 200
    assert r2.json() == {"ok": True, "jumlah_item": 1}
    assert client.get(f"/api/products/{p1}").json()["qty"] == 33


def test_opname_terapkan_scan_tidak_ada(tmp_path):
    client, _ = _client(tmp_path)
    r = client.post("/api/opname/999/terapkan")
    assert r.status_code == 404


def test_opname_terapkan_dua_kali_ditolak(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": p1, "qty_fisik": 33}],
    })
    scan_id = r.json()["scan_id"]
    assert client.post(f"/api/opname/{scan_id}/terapkan").status_code == 200
    assert client.get(f"/api/products/{p1}").json()["qty"] == 33

    # stok berubah lagi setelah terapkan pertama (jual/penyesuaian)
    client.post("/api/adjustments",
                json={"product_id": p1, "delta": -3, "alasan": "koreksi"})
    assert client.get(f"/api/products/{p1}").json()["qty"] == 30

    # terapkan kedua: 409, stok TIDAK tertimpa snapshot basi
    r2 = client.post(f"/api/opname/{scan_id}/terapkan")
    assert r2.status_code == 409
    assert "sudah diterapkan" in r2.json()["detail"].lower()
    assert client.get(f"/api/products/{p1}").json()["qty"] == 30


def test_opname_terapkan_kalah_balapan_jadi_409_bukan_500(tmp_path, monkeypatch):
    # Cek terapkan_pada di endpoint cuma untuk pesan; guard sebenarnya
    # compare-and-set di db.terapkan_opname. Kalau request lain menang balapan
    # SETELAH cek itu lolos, helper melempar dan endpoint harus tetap menjawab
    # 409 — bukan bocor jadi 500. Cabang except itu mustahil dipicu lewat
    # TestClient satu thread, jadi balapannya disimulasikan di sini.
    client, p1 = _client(tmp_path)
    scan_id = client.post("/api/opname-manual", json={
        "items": [{"product_id": p1, "qty_fisik": 33}],
    }).json()["scan_id"]

    def kalah_balapan(con, sid):
        raise db.OpnameSudahDiterapkan(f"Scan #{sid} sudah diterapkan")

    monkeypatch.setattr(db, "terapkan_opname", kalah_balapan)
    r = client.post(f"/api/opname/{scan_id}/terapkan")
    assert r.status_code == 409
    assert "sudah diterapkan" in r.json()["detail"].lower()


def test_opname_manual_terapkan_true_tandai_terapkan_pada(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/opname-manual", json={
        "terapkan": True,
        "items": [{"product_id": p1, "qty_fisik": 37}],
    })
    scan_id = r.json()["scan_id"]
    rows = client.get("/api/scans").json()
    row = next(s for s in rows if s["id"] == scan_id)
    assert row["terapkan_pada"] is not None
    # dan terapkan manual kedua ditolak
    assert client.post(f"/api/opname/{scan_id}/terapkan").status_code == 409


def test_report_punya_key_scan(tmp_path):
    client, p1 = _client(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": p1, "qty_fisik": 37}],
    })
    scan_id = r.json()["scan_id"]
    rep = client.get(f"/report/{scan_id}").json()
    assert rep["scan"]["id"] == scan_id
    assert rep["scan"]["terapkan_pada"] is None


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


# ---- POST /products: field opsional harga_jual + stok_minimum ----

class _FakeEmbedderPil:
    def embed_pil(self, img):
        return np.zeros(4, dtype=np.float32)


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_create_product_dengan_harga_jual_dan_stok_minimum(tmp_path):
    dbp = str(tmp_path / "t.db")
    client = TestClient(create_app(db_path=dbp, embedder=_FakeEmbedderPil()))
    r = client.post(
        "/products",
        data={"nama": "Teh Botol", "harga_modal": "3000", "qty_awal": "5",
              "harga_jual": "3500", "stok_minimum": "2"},
        files=[("fotos", ("a.png", _png_bytes(), "image/png"))],
    )
    assert r.status_code == 200
    pid = r.json()["product_id"]
    detail = client.get(f"/api/products/{pid}").json()
    assert detail["harga_jual"] == 3500
    assert detail["stok_minimum"] == 2
    assert detail["qty"] == 5
