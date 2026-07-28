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
