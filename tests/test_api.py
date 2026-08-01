import numpy as np
from fastapi.testclient import TestClient

from stoklens import db
from stoklens.api import create_app


def _seeded(tmp_path):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    pid = db.add_product(con, "Indomie", 3200, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 40)
    sid = db.add_scan(con, video_ref="v.mp4")
    db.add_scan_item(con, sid, pid, 37, 0.9, "2026-08-01", 2)
    con.close()
    return dbp, sid


def test_report_endpoint(tmp_path):
    dbp, sid = _seeded(tmp_path)
    client = TestClient(create_app(db_path=dbp))
    rep = client.get(f"/report/{sid}").json()
    assert rep["items"][0]["selisih"] == -3
    assert rep["total_shrinkage_rp"] == 9600


def test_report_404_untuk_scan_tak_ada(tmp_path):
    dbp, _ = _seeded(tmp_path)
    client = TestClient(create_app(db_path=dbp))
    assert client.get("/report/99999").status_code == 404


def test_root_redirect_ke_ui(tmp_path):
    dbp, _ = _seeded(tmp_path)
    client = TestClient(create_app(db_path=dbp))
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/ui/beranda"


def test_scans_endpoint_terima_count_mode(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    captured = {}

    def stub_run_scan(con_, embedder, video_path, lokasi_rak=None, count_mode="line", **kw):
        captured["count_mode"] = count_mode
        return db.add_scan(con_, video_ref=str(video_path), lokasi_rak=lokasi_rak)

    monkeypatch.setattr("stoklens.scan.run_scan", stub_run_scan)
    client = TestClient(create_app(db_path=dbp, embedder=object()))
    r = client.post(
        "/scans",
        files={"video": ("v.mp4", b"x", "video/mp4")},
        data={"lokasi_rak": "Rak 1", "count_mode": "track"},
    )
    assert r.status_code == 200
    assert captured["count_mode"] == "track"


# --- lokasi file DB (dipakai docker compose lewat env) ---------------------
# Container me-mount volume ke /app/data lalu set STOKLENS_DB ke situ. Tanpa
# ini DB tertulis di layer container dan hilang tiap `docker compose down`.

def test_db_path_diambil_dari_env(tmp_path, monkeypatch):
    dbp = tmp_path / "dari-env.db"
    monkeypatch.setenv("STOKLENS_DB", str(dbp))
    client = TestClient(create_app())
    assert client.get("/api/products").status_code == 200
    assert dbp.exists()


def test_folder_induk_db_dibuat_kalau_belum_ada(tmp_path, monkeypatch):
    # Kasus nyata: compose menaruh DB di /app/data yang baru ada setelah volume
    # ter-mount. Tanpa mkdir eksplisit, sqlite gagal "unable to open database
    # file" — dan sebelumnya ini cuma selamat karena efek samping mkdir milik
    # /crops, yang tujuan tertulisnya sama sekali lain.
    dbp = tmp_path / "belum" / "ada" / "stoklens.db"
    monkeypatch.setenv("STOKLENS_DB", str(dbp))
    client = TestClient(create_app())
    assert client.get("/api/products").status_code == 200
    assert dbp.exists()


def test_db_path_eksplisit_menang_atas_env(tmp_path, monkeypatch):
    # Test lama memanggil create_app(db_path=...) — argumen tidak boleh kalah
    # oleh env yang kebetulan ter-set di mesin developer.
    dari_env = tmp_path / "env.db"
    monkeypatch.setenv("STOKLENS_DB", str(dari_env))
    eksplisit = tmp_path / "eksplisit.db"
    client = TestClient(create_app(db_path=str(eksplisit)))
    assert client.get("/api/products").status_code == 200
    assert eksplisit.exists()
    assert not dari_env.exists()


# --- validasi input (edge case review 2026-07-30) --------------------------
# Semua kasus di bawah sebelumnya lolos atau meledak jadi 500. Yang diperbaiki
# di sini bukan cuma nilainya, tapi ketidakkonsistenannya: /api/adjustments
# SUDAH menjaga stok negatif dan /api/scans-foto SUDAH memvalidasi file bukan
# gambar jadi 400, sementara jalur lain tidak.

def _app(tmp_path, **kw):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    pid = db.add_product(con, "Indomie", 3200, np.zeros(4, dtype=np.float32))
    db.add_product(con, "Yakult", 2000, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 40)
    con.close()
    return TestClient(create_app(db_path=dbp, **kw)), pid


def test_qty_fisik_negatif_ditolak(tmp_path):
    """Sebelumnya lolos dan menulis stok ledger jadi negatif."""
    client, pid = _app(tmp_path)
    r = client.post("/api/opname-manual",
                    json={"items": [{"product_id": pid, "qty_fisik": -50}]})
    assert r.status_code == 422
    assert db.get_stock_map(db.connect(str(tmp_path / "t.db")))[pid] == 40


def test_patch_harga_negatif_ditolak(tmp_path):
    client, pid = _app(tmp_path)
    for field in ("harga_modal", "harga_jual", "stok_minimum"):
        r = client.patch(f"/api/products/{pid}", json={field: -1})
        assert r.status_code == 422, field


def test_patch_nama_duplikat_400_bukan_500(tmp_path):
    """products.nama UNIQUE — IntegrityError harus jadi 400 dengan pesan jelas."""
    client, pid = _app(tmp_path)
    r = client.patch(f"/api/products/{pid}", json={"nama": "Yakult"})
    assert r.status_code == 400
    assert "Yakult" in r.json()["detail"]


def test_enrollment_tanpa_foto_400_bukan_500(tmp_path):
    client, _ = _app(tmp_path, embedder=object())
    r = client.post("/products", data={"nama": "Baru", "harga_modal": 1000})
    assert r.status_code == 400
    assert "foto" in r.json()["detail"].lower()


def test_enrollment_file_bukan_gambar_400_bukan_500(tmp_path):
    """Samakan dengan /api/scans-foto yang sudah mengembalikan 400."""
    client, _ = _app(tmp_path, embedder=object())
    r = client.post("/products", data={"nama": "Baru", "harga_modal": 1000},
                    files={"fotos": ("rusak.jpg", b"ini teks biasa", "image/jpeg")})
    assert r.status_code == 400
    assert "rusak.jpg" in r.json()["detail"]


def test_enrollment_angka_negatif_ditolak(tmp_path):
    client, _ = _app(tmp_path, embedder=object())
    for field in ("harga_modal", "qty_awal", "stok_minimum"):
        data = {"nama": f"P-{field}", "harga_modal": 1000, field: -1}
        r = client.post("/products", data=data,
                        files={"fotos": ("a.jpg", b"x", "image/jpeg")})
        assert r.status_code == 422, field


# --- validasi isi /api/opname-manual (backlog #8, #9, #10) -----------------
# Ketiganya sebelumnya 200. Yang paling merugikan #10: dua baris untuk produk
# yang sama ikut ke laporan, jadi total_shrinkage_rp menghitung ganda dan user
# melihat angka rupiah kerugian yang salah. UI checklist tidak bisa menghasilkan
# dobel; yang ditutup di sini jalur API langsung.

def test_opname_manual_items_kosong_ditolak(tmp_path):
    client, _ = _app(tmp_path)
    r = client.post("/api/opname-manual", json={"items": [], "terapkan": True})
    assert r.status_code == 400
    assert r.json()["detail"] == "Opname harus berisi minimal satu barang"


def test_opname_manual_product_id_dobel_ditolak(tmp_path):
    """Menggabungkan qty yang dobel akan menyembunyikan bug di sisi pemanggil."""
    client, pid = _app(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": pid, "qty_fisik": 3},
                  {"product_id": pid, "qty_fisik": 7}],
        "terapkan": True,
    })
    assert r.status_code == 400
    assert r.json()["detail"] == f"product_id dobel dalam satu opname: {pid}"


def test_opname_manual_product_id_tak_dikenal_ditolak(tmp_path):
    """get_report_rows JOIN ke products, jadi id salah terbuang diam-diam."""
    client, pid = _app(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": pid, "qty_fisik": 5},
                  {"product_id": 9999, "qty_fisik": 5},
                  {"product_id": 4242, "qty_fisik": 5}],
    })
    assert r.status_code == 400
    # Daftar id diurutkan supaya pesannya deterministik.
    assert r.json()["detail"] == "product_id tidak dikenal: 4242, 9999"


def test_opname_manual_terima_produk_yang_belum_punya_ledger(tmp_path):
    """"Dikenal" = ada di tabel products, BUKAN ada di stock_ledger.

    Fixture sengaja membuat Yakult tanpa set_stock, jadi dia tidak punya baris
    stock_ledger. Kalau cek keberadaan dilakukan lewat get_stock_map, produk
    yang baru di-enroll dan belum pernah di-opname akan ditolak sebagai "tidak
    dikenal" — persis produk yang paling butuh opname pertamanya.
    """
    client, _ = _app(tmp_path)
    con = db.connect(str(tmp_path / "t.db"))
    yakult = next(p["id"] for p in db.all_products(con) if p["nama"] == "Yakult")
    assert yakult not in db.get_stock_map(con), "prasyarat: Yakult tanpa ledger"
    r = client.post("/api/opname-manual",
                    json={"items": [{"product_id": yakult, "qty_fisik": 5}]})
    assert r.status_code == 200


def test_opname_manual_tolak_dulu_baru_id_tak_dikenal(tmp_path):
    """Dobel dicek sebelum id tak dikenal — pesannya harus soal dobel."""
    client, _ = _app(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": 9999, "qty_fisik": 1},
                  {"product_id": 9999, "qty_fisik": 2}],
    })
    assert r.status_code == 400
    assert "dobel" in r.json()["detail"]


def test_opname_manual_ditolak_tidak_menyisakan_scan(tmp_path):
    """Sebelumnya scans + scan_items sudah tertulis sebelum validasi apa pun."""
    client, pid = _app(tmp_path)
    tolakan = [
        {"items": []},
        {"items": [{"product_id": pid, "qty_fisik": 1},
                   {"product_id": pid, "qty_fisik": 2}]},
        {"items": [{"product_id": 9999, "qty_fisik": 1}]},
    ]
    for body in tolakan:
        assert client.post("/api/opname-manual", json=body).status_code == 400
    con = db.connect(str(tmp_path / "t.db"))
    assert db.list_scans(con) == []


def test_opname_manual_sah_tetap_200(tmp_path):
    client, pid = _app(tmp_path)
    r = client.post("/api/opname-manual", json={
        "items": [{"product_id": pid, "qty_fisik": 37}], "terapkan": True})
    assert r.status_code == 200
    body = r.json()
    assert body["diterapkan"] is True
    assert body["report"]["items"][0]["selisih"] == -3
    assert db.get_stock_map(db.connect(str(tmp_path / "t.db")))[pid] == 37
