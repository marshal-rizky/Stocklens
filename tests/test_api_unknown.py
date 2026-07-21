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
    con.close()
    return dbp, sid, pid


def _client(dbp, tmp_path, **kw):
    crops_dir = tmp_path / "crops"
    # embedder=object(): kalau endpoint sempat memanggil get_embedder()/CLIP,
    # ini bakal meledak (object() bukan embedder yang valid) — bukti CLIP
    # tidak pernah disentuh oleh endpoint unknown crop.
    return TestClient(create_app(db_path=dbp, embedder=object(),
                                  crops_dir=crops_dir, **kw))


def test_crops_mount_serves_file(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    crops_dir = tmp_path / "crops"
    folder = crops_dir / str(sid)
    folder.mkdir(parents=True)
    (folder / "abc.jpg").write_bytes(b"fake-jpeg-bytes")

    client = TestClient(create_app(db_path=dbp, embedder=object(), crops_dir=crops_dir))
    r = client.get(f"/crops/{sid}/abc.jpg")
    assert r.status_code == 200
    assert r.content == b"fake-jpeg-bytes"


def test_list_unknown_happy_path(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/abcd1234.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    con.close()

    client = _client(dbp, tmp_path)
    r = client.get(f"/api/scans/{sid}/unknown")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == cid
    assert item["crop_url"] == f"/crops/{sid}/abcd1234.jpg"
    assert "created_at" in item
    assert "crop_path" not in item
    assert "embedding" not in item


def test_list_unknown_excludes_resolved(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    db.resolve_unknown_crop(con, cid, pid)
    con.close()

    client = _client(dbp, tmp_path)
    r = client.get(f"/api/scans/{sid}/unknown")
    assert r.status_code == 200
    assert r.json() == []


def test_assign_happy_path(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/assign", json={"product_id": pid})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["product_id"] == pid
    assert body["jumlah_galeri"] == 1

    con = db.connect(dbp)
    assert db.count_product_embeddings(con, pid) == 1
    rows = con.execute(
        "SELECT embedding FROM product_embeddings WHERE product_id=?", (pid,)
    ).fetchall()
    emb = np.frombuffer(rows[0]["embedding"], dtype=np.float32)
    assert np.array_equal(emb, np.array([1, 2, 3, 4], dtype=np.float32))
    crop = db.get_unknown_crop(con, cid)
    assert crop["product_id"] == pid
    con.close()


def test_assign_404_crop_not_found(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    client = _client(dbp, tmp_path)
    r = client.post("/api/unknown/999/assign", json={"product_id": pid})
    assert r.status_code == 404


def test_assign_404_product_not_found(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/assign", json={"product_id": 999})
    assert r.status_code == 404


def test_assign_409_already_resolved(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    db.resolve_unknown_crop(con, cid, pid)
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/assign", json={"product_id": pid})
    assert r.status_code == 409


def test_produk_baru_happy_path(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([5, 6, 7, 8], dtype=np.float32))
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/produk-baru", json={
        "nama": "Teh Botol",
        "harga_modal": 4000,
        "harga_jual": 5500,
        "stok_minimum": 5,
        "qty_awal": 12,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    new_pid = body["product_id"]

    con = db.connect(dbp)
    p = db.get_product(con, new_pid)
    assert p["nama"] == "Teh Botol"
    assert p["harga_modal"] == 4000
    assert p["harga_jual"] == 5500
    assert p["stok_minimum"] == 5
    stock = db.get_stock_map(con)
    assert stock[new_pid] == 12
    crop = db.get_unknown_crop(con, cid)
    assert crop["product_id"] == new_pid
    con.close()


def test_produk_baru_404_crop_not_found(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    client = _client(dbp, tmp_path)
    r = client.post("/api/unknown/999/produk-baru", json={
        "nama": "Barang X", "harga_modal": 1000,
    })
    assert r.status_code == 404


def test_produk_baru_409_already_resolved(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    db.resolve_unknown_crop(con, cid, pid)
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/produk-baru", json={
        "nama": "Barang Y", "harga_modal": 1000,
    })
    assert r.status_code == 409


def test_produk_baru_400_duplicate_nama(tmp_path):
    dbp, sid, pid = _seeded(tmp_path)
    con = db.connect(dbp)
    cid = db.add_unknown_crop(con, sid, f"data/crops/{sid}/x.jpg",
                              np.array([1, 2, 3, 4], dtype=np.float32))
    con.close()

    client = _client(dbp, tmp_path)
    r = client.post(f"/api/unknown/{cid}/produk-baru", json={
        "nama": "Indomie", "harga_modal": 1000,
    })
    assert r.status_code == 400
