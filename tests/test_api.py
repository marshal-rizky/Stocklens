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


def test_dashboard_html(tmp_path):
    dbp, _ = _seeded(tmp_path)
    client = TestClient(create_app(db_path=dbp))
    html = client.get("/").text
    assert "Indomie" in html and "9.600" in html
