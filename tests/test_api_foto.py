import cv2
import numpy as np
from fastapi.testclient import TestClient

from stoklens import db
from stoklens.api import MAKS_BYTE_PER_FOTO, MAKS_FOTO_PER_SCAN, create_app
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
    # Crop unknown ditulis ke DIR_CROPS_DEFAULT yang RELATIF ke cwd — tanpa
    # chdir, tiap kali pytest jalan repo kotor oleh file JPEG asli.
    # Test lain memakai parameter `dir_crops`, tapi endpoint /api/scans-foto
    # belum meneruskannya (itu urusan Unit 3 yang sekalian mount StaticFiles),
    # jadi di sini chdir masih cara terbersih.
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


def test_scan_foto_tolak_kelebihan_jumlah(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _client(tmp_path)
    # Isinya sengaja bukan gambar: kalau jumlah dicek sebelum decode (yang kita
    # mau), pesannya soal jumlah. Kalau ceknya kesorong ke belakang, yang keluar
    # "File bukan gambar valid" dan test ini merah.
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", (f"f{i}.png", b"bukan gambar", "image/png"))
               for i in range(MAKS_FOTO_PER_SCAN + 1)],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    pesan = r.json()["detail"]
    assert str(MAKS_FOTO_PER_SCAN) in pesan
    assert str(MAKS_FOTO_PER_SCAN + 1) in pesan
    assert "bukan gambar valid" not in pesan


def test_scan_foto_terima_tepat_batas_jumlah(tmp_path, monkeypatch):
    # Batasnya inklusif: tepat MAKS_FOTO_PER_SCAN masih harus lolos.
    monkeypatch.chdir(tmp_path)
    client = _client(tmp_path)
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", (f"f{i}.png", _jpeg(), "image/png"))
               for i in range(MAKS_FOTO_PER_SCAN)],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 200


def test_scan_foto_tolak_file_terlalu_besar(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _client(tmp_path)
    # Byte mentah, bukan gambar: kalau ukuran dicek sebelum decode (yang kita
    # mau), pesannya soal ukuran. Kalau kesorong ke belakang, jawabannya jadi
    # "File bukan gambar valid" dan test ini merah.
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("raksasa.png", b"\0" * (MAKS_BYTE_PER_FOTO + 1),
                          "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    pesan = r.json()["detail"]
    assert "raksasa.png" in pesan
    assert str(MAKS_BYTE_PER_FOTO // (1024 * 1024)) in pesan
    assert "bukan gambar valid" not in pesan

    # Batasnya inklusif juga di sisi ukuran: tepat MAKS_BYTE_PER_FOTO lolos
    # gerbang ukuran. Isinya tetap bukan gambar, jadi yang ditolak decode —
    # yang penting alasannya bukan "terlalu besar".
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("pas.png", b"\0" * MAKS_BYTE_PER_FOTO, "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert "terlalu besar" not in r.json()["detail"]


def test_pesan_batas_ikut_konstanta(tmp_path, monkeypatch):
    # Angka di pesan galat harus dibaca dari konstantanya, bukan ditulis ulang
    # sebagai literal di dalam string — kalau batasnya disetel ulang, pesannya
    # harus ikut. Sekalian: batas kecil bikin test ini murah.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("stoklens.api.MAKS_FOTO_PER_SCAN", 2)
    monkeypatch.setattr("stoklens.api.MAKS_BYTE_PER_FOTO", 1024 * 1024)
    client = _client(tmp_path)

    r = client.post(
        "/api/scans-foto",
        files=[("fotos", (f"f{i}.png", _jpeg(), "image/png")) for i in range(3)],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Maksimal 2 foto per scan, dikirim 3"

    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("besar.png", b"\0" * (1024 * 1024 + 1), "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Foto besar.png terlalu besar (1.0 MB), maksimal 1 MB"
