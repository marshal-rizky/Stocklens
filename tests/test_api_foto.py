import cv2
import numpy as np
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

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

    # Ukuran di pesan harus ukuran file sebenarnya, bukan angka batasnya lagi:
    # 2,5 MB sengaja jauh dari batas 1 MB supaya keduanya tidak bisa tertukar.
    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("besar.png", b"\0" * (5 * 512 * 1024), "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Foto besar.png terlalu besar (2.5 MB), maksimal 1 MB"


def test_nilai_batas_sesuai_spec():
    # Penyeimbang desain "pesan ikut konstanta": semua test lain menurunkan
    # ekspektasinya DARI konstanta ini, jadi tanpa assertion nilai, batasnya
    # bisa digeser sejauh apa pun (mis. jadi 200 foto) tanpa satu test pun merah.
    assert MAKS_FOTO_PER_SCAN == 20
    assert MAKS_BYTE_PER_FOTO == 15 * 1024 * 1024


def test_tolak_file_besar_walau_size_tak_diketahui(tmp_path, monkeypatch):
    # UploadFile.size boleh None (tipenya `int | None`). Parser multipart selalu
    # mengisinya, jadi cabang ini tak terjangkau lewat HTTP biasa — di sini
    # None-nya dipaksa supaya fallback len(data) benar-benar teruji: tanpa itu,
    # size=None jadi lubang yang meloloskan file besar.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("stoklens.api.MAKS_BYTE_PER_FOTO", 1024 * 1024)
    init_asli = UploadFile.__init__

    def init_tanpa_size(self, file, *, size=None, **kw):
        init_asli(self, file, size=None, **kw)

    monkeypatch.setattr(UploadFile, "__init__", init_tanpa_size)
    client = _client(tmp_path)

    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("besar.png", b"\0" * (2 * 1024 * 1024), "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Foto besar.png terlalu besar (2.0 MB), maksimal 1 MB"


def test_batas_menolak_tanpa_membaca_isi_foto(tmp_path, monkeypatch):
    # Inti dari "ditolak murah": kiriman yang melewati batas tidak boleh menarik
    # satu byte pun ke RAM. Tanpa test ini, memindahkan cek jumlah ke belakang
    # loop baca (semua foto sudah di memori, tapi masih sebelum decode) lolos
    # tanpa terdeteksi — persis regresi yang bikin batasnya jadi tak berguna.
    monkeypatch.chdir(tmp_path)
    client = _client(tmp_path)
    dibaca = []
    read_asli = UploadFile.read

    async def read_tercatat(self, size=-1):
        dibaca.append(self.filename)
        return await read_asli(self, size)

    # Ditambal di kelas basis starlette; UploadFile milik FastAPI mewarisi read
    # dari sini, jadi satu tambalan menutup keduanya.
    monkeypatch.setattr(UploadFile, "read", read_tercatat)

    r = client.post(
        "/api/scans-foto",
        files=[("fotos", (f"f{i}.png", _jpeg(), "image/png"))
               for i in range(MAKS_FOTO_PER_SCAN + 1)],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert dibaca == []

    r = client.post(
        "/api/scans-foto",
        files=[("fotos", ("raksasa.png", b"\0" * (MAKS_BYTE_PER_FOTO + 1),
                          "image/png"))],
        data={"read_expiry": "false"},
    )
    assert r.status_code == 400
    assert dibaca == []
