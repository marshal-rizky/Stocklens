"""Koneksi SQLite tidak boleh menggantung setelah request selesai.

Sebelumnya tiap endpoint memanggil `con()` lalu menyerahkan penutupannya ke
garbage collector. Di CPython itu "biasanya jalan", tapi tidak dijamin: koneksi
yang masih hidup menahan file DB (di Windows sampai file-nya tidak bisa dihapus)
dan pada beban banyak request menumpuk sampai batas file descriptor.

CARA MENGUKUR — jangan diubah tanpa paham:
`db.connect` diganti versi yang menghitung buka/tutup, lewat parameter `factory`
yang memang sudah disediakan `db.connect` untuk keperluan ini. Yang diperiksa
selisihnya (dibuka - ditutup), bukan cuma "ada yang ditutup": endpoint yang lupa
diikutkan tetap memanggil `db.connect` sehingga ikut terhitung dibuka, dan
selisihnya yang membongkarnya.

Test terakhir di berkas ini memakai request BERSAMAAN dan bukan basa-basi:
lihat komentarnya. Dengan TestClient yang mengirim satu request pada satu waktu,
seluruh test di atas tetap hijau walau koneksinya lahir di thread yang salah.
"""
import asyncio
import sqlite3

import cv2
import httpx
import numpy as np
from fastapi.testclient import TestClient

from stoklens import db
from stoklens.api import create_app


def _pantau(monkeypatch):
    """Ganti db.connect dengan versi yang mencatat buka/tutup. Return catatannya."""
    asli = db.connect
    catatan = {"dibuka": 0, "ditutup": 0}

    class Terpantau(sqlite3.Connection):
        # close() boleh dipanggil berkali-kali pada koneksi yang sama (sqlite3
        # membolehkannya); tanpa penanda ini satu koneksi bisa menutup "dua kali"
        # dan menyembunyikan koneksi lain yang benar-benar bocor.
        def close(self):
            if not getattr(self, "_tercatat_tutup", False):
                self._tercatat_tutup = True
                catatan["ditutup"] += 1
            super().close()

    def connect_terpantau(path, factory=sqlite3.Connection):
        catatan["dibuka"] += 1
        return asli(path, factory=Terpantau)

    monkeypatch.setattr(db, "connect", connect_terpantau)
    return catatan


def _seeded(tmp_path):
    dbp = str(tmp_path / "t.db")
    con = db.connect(dbp)
    pid = db.add_product(con, "Indomie", 3200, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 40)
    sid = db.add_scan(con, video_ref="v.mp4")
    db.add_scan_item(con, sid, pid, 37, 0.9, "2026-08-01", 2)
    con.close()
    return dbp, pid, sid


def _jpeg():
    return cv2.imencode(".jpg", np.zeros((32, 32, 3), np.uint8))[1].tobytes()


def test_koneksi_ditutup_setelah_request_sukses(tmp_path, monkeypatch):
    dbp, pid, sid = _seeded(tmp_path)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp))

    permintaan = [
        client.get("/api/products"),
        client.get(f"/api/products/{pid}"),
        client.get("/api/dashboard"),
        client.get("/api/scans"),
        client.get(f"/report/{sid}"),
        client.get(f"/api/scans/{sid}/unknown"),
        client.patch(f"/api/products/{pid}", json={"harga_modal": 3300}),
        client.post("/api/adjustments",
                    json={"product_id": pid, "delta": -1, "alasan": "rusak"}),
        client.post("/api/opname-manual",
                    json={"items": [{"product_id": pid, "qty_fisik": 5}],
                          "terapkan": True}),
    ]
    for r in permintaan:
        assert r.status_code == 200, r.text

    assert catatan["dibuka"] == len(permintaan), catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_di_export_csv(tmp_path, monkeypatch):
    # Dipisah dari test di atas: export satu-satunya endpoint yang merakit body
    # sendiri. Kalau suatu saat diubah jadi streaming, koneksinya akan sudah
    # tertutup saat body ditarik — test ini yang akan meributkannya.
    dbp, _, _ = _seeded(tmp_path)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp))

    r = client.get("/api/export/stok.csv")
    assert r.status_code == 200
    assert "Indomie" in r.text
    assert catatan["dibuka"] == 1, catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_walau_endpoint_melempar_httpexception(tmp_path, monkeypatch):
    # Justru jalur galat yang paling gampang bocor: penutupan yang ditulis
    # sebagai baris terakhir handler (bukan `with`/`finally`) lolos di jalur
    # sukses dan bocor di sini.
    dbp, pid, _ = _seeded(tmp_path)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp))

    permintaan = [
        client.get("/report/99999"),
        client.get("/api/products/99999"),
        client.patch("/api/products/99999", json={"harga_modal": 1}),
        client.post("/api/adjustments",
                    json={"product_id": 99999, "delta": 1, "alasan": "x"}),
        client.post("/api/opname-manual", json={"items": []}),
        client.post("/api/opname/99999/terapkan"),
        client.post("/api/unknown/99999/assign", json={"product_id": pid}),
        client.post("/api/unknown/99999/produk-baru",
                    json={"nama": "Baru", "harga_modal": 1000}),
    ]
    for r in permintaan:
        assert r.status_code in (400, 404, 409), r.text

    assert catatan["dibuka"] == len(permintaan), catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_di_enrollment(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def enroll_stub(con, embedder, nama, harga_modal, foto_paths, **kw):
        return db.add_product(con, nama, harga_modal, np.zeros(4, dtype=np.float32))

    monkeypatch.setattr("stoklens.enroll.enroll_product", enroll_stub)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp, embedder=object()))

    r = client.post("/products", files={"fotos": ("a.jpg", _jpeg(), "image/jpeg")},
                    data={"nama": "Indomie", "harga_modal": 3200})
    assert r.status_code == 200, r.text
    assert catatan["dibuka"] == 1, catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_di_scan_video(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def run_scan_stub(con, embedder, video_path, **kw):
        return db.add_scan(con, video_ref=str(video_path))

    monkeypatch.setattr("stoklens.scan.run_scan", run_scan_stub)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp, embedder=object()))

    r = client.post("/scans", files={"video": ("v.mp4", b"x", "video/mp4")})
    assert r.status_code == 200, r.text
    assert catatan["dibuka"] == 1, catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_di_scan_foto(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def scan_photos_stub(con, embedder, images, **kw):
        return db.add_scan(con, tipe="foto")

    monkeypatch.setattr("stoklens.photo.scan_photos", scan_photos_stub)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp, embedder=object(),
                                   photo_detector=lambda img: []))

    r = client.post("/api/scans-foto",
                    files={"fotos": ("a.jpg", _jpeg(), "image/jpeg")})
    assert r.status_code == 200, r.text
    assert catatan["dibuka"] == 1, catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_ditutup_saat_endpoint_berat_melempar_httpexception(tmp_path,
                                                                    monkeypatch):
    # Mengunci bahwa HTTPException yang dilempar dari DALAM fungsi threadpool,
    # setelah koneksinya dibuka, tidak melewati penutupan koneksi.
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def scan_photos_gagal(con, embedder, images, **kw):
        from fastapi import HTTPException
        raise HTTPException(400, "gagal sengaja")

    monkeypatch.setattr("stoklens.photo.scan_photos", scan_photos_gagal)
    catatan = _pantau(monkeypatch)
    client = TestClient(create_app(db_path=dbp, embedder=object(),
                                   photo_detector=lambda img: []))

    r = client.post("/api/scans-foto",
                    files={"fotos": ("a.jpg", _jpeg(), "image/jpeg")})
    assert r.status_code == 400, r.text
    assert catatan["dibuka"] == 1, catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan


def test_koneksi_aman_saat_request_bersamaan(tmp_path, monkeypatch):
    """Koneksi harus lahir dan mati di thread yang sama dengan pemakainya.

    Ini test yang menahan godaan memindahkan pembuatan koneksi ke dependency
    FastAPI (`Depends`). Endpoint di sini `def` (sinkron), dan FastAPI
    menjalankan dependency sinkron di worker threadpool yang BELUM TENTU sama
    dengan yang menjalankan handler-nya. Dengan check_same_thread=True bawaan
    sqlite3, koneksi dari dependency lalu dipakai di handler melempar
    ProgrammingError.

    Kenapa harus BERSAMAAN, dan bukan TestClient seperti test lain di berkas
    ini: saat request datang satu-satu, anyio memakai ulang satu worker yang
    menganggur sehingga dependency dan handler kebetulan se-thread — versi yang
    rusak pun hijau. Baru dengan beberapa request paralel worker-nya berbeda dan
    kesalahannya muncul. Jangan diturunkan jadi sekuensial.
    """
    dbp, pid, _ = _seeded(tmp_path)
    catatan = _pantau(monkeypatch)
    app = create_app(db_path=dbp)

    async def tembak():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t",
                                     timeout=30) as cl:
            return await asyncio.gather(*[cl.get("/api/products")
                                          for _ in range(20)])

    hasil = asyncio.run(tembak())
    for r in hasil:
        assert r.status_code == 200, r.text
    assert catatan["dibuka"] == len(hasil), catatan
    assert catatan["dibuka"] - catatan["ditutup"] == 0, catatan
