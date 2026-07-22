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
