import cv2
import numpy as np
from fastapi.testclient import TestClient

from stoklens import db
from stoklens.api import create_app
from tests.test_photo import FakeEmbedder, _fixture_image, fake_detector


def _client(tmp_path):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    db.add_product(con, "Merah", 1000, np.array([1, 0], dtype=np.float32))
    db.set_stock(con, 1, 3)
    con.close()
    return TestClient(create_app(db_path=dbp, embedder=FakeEmbedder(),
                                 photo_detector=fake_detector))


def _jpeg():
    ok, buf = cv2.imencode(".png", _fixture_image())  # png = lossless, warna aman
    assert ok
    return buf.tobytes()


def test_scan_foto_endpoint(tmp_path, monkeypatch):
    # Crop unknown ditulis ke `data/crops/` RELATIF ke cwd — tanpa chdir,
    # tiap kali pytest jalan repo kotor oleh file JPEG asli.
    monkeypatch.chdir(tmp_path)
    client = _client(tmp_path)
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("a.png", _jpeg(), "image/png")),
               ("fotos", ("b.png", _jpeg(), "image/png"))],
        data={"lokasi_rak": "Rak 1", "read_expiry": "false"},
    )
    assert r.status_code == 200
    body = r.json()
    rep = {i["nama"]: i for i in body["report"]["items"]}
    assert rep["Merah"]["qty_terdeteksi"] == 2
    assert rep["Merah"]["selisih"] == -1          # tercatat 3, fisik 2
    # tipe scan tercatat sebagai foto
    client2_scan = db.connect(str(tmp_path / "t.db"))
    assert db.get_scan(client2_scan, body["scan_id"])["tipe"] == "foto"
