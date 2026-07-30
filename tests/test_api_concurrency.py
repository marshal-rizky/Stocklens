"""Endpoint berat tidak boleh memblokir event loop.

Scan foto, scan video, dan enrollment memanggil pipeline sinkron yang berat
(YOLO + CLIP + OCR). Kalau kerja itu jalan di atas event loop, SELURUH aplikasi
beku selama scan — halaman tidak bisa dibuka, tombol tidak merespons. Untuk scan
foto yang UI-nya sendiri menjanjikan "±30 dtk" itu berarti setengah menit
aplikasi terlihat mati, dan dengan OCR di puluhan crop bisa menit.

CARA MENGUKUR — jangan diubah tanpa paham:
Yang diukur adalah waktu ABSOLUT dari satu titik awal bersama, bukan durasi
masing-masing request. Mengukur durasi GET saja TIDAK mendeteksi blokade:
kalau loop terblokir, `asyncio.sleep()` sebelum GET ikut kelaparan sehingga
GET-nya baru mulai belakangan lalu selesai cepat — durasinya terlihat sehat
padahal server beku.

Test-nya sinkron dan memakai `asyncio.run()` sendiri, BUKAN pytest-asyncio —
CI sengaja memasang daftar dependensi minimal, dan menambah plugin cuma untuk
tiga test tidak sepadan.
"""
import asyncio
import time

import cv2
import httpx
import numpy as np

from stoklens import db
from stoklens.api import create_app

# Cukup lama untuk terukur, cukup pendek untuk tidak memperlambat CI.
KERJA = 0.6
JEDA_SEBELUM_GET = 0.1


def _jpeg():
    return cv2.imencode(".jpg", np.zeros((32, 32, 3), np.uint8))[1].tobytes()


async def _absolut(app, path_berat, files, data=None):
    """Jalankan request berat + GET bersamaan; return (t_selesai_berat, t_selesai_get)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t",
                                 timeout=30) as cl:
        t0 = time.perf_counter()

        async def berat():
            r = await cl.post(path_berat, files=files, data=data or {})
            assert r.status_code == 200, r.text
            return time.perf_counter() - t0

        async def ringan():
            await asyncio.sleep(JEDA_SEBELUM_GET)
            r = await cl.get("/api/products")
            assert r.status_code == 200
            return time.perf_counter() - t0

        return await asyncio.gather(berat(), ringan())


def test_scan_foto_tidak_memblokir_endpoint_lain(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def scan_lambat(con, embedder, images, **kw):
        time.sleep(KERJA)
        return db.add_scan(con, tipe="foto")

    monkeypatch.setattr("stoklens.photo.scan_photos", scan_lambat)
    app = create_app(db_path=dbp, embedder=object(), photo_detector=lambda img: [])

    t_scan, t_get = asyncio.run(_absolut(
        app, "/api/scans-foto", {"fotos": ("a.jpg", _jpeg(), "image/jpeg")}))

    assert t_scan >= KERJA, "stub tidak terpakai — test ini tidak menguji apa pun"
    assert t_get < t_scan, (
        f"GET selesai di {t_get:.2f}s, scan di {t_scan:.2f}s — event loop terblokir")


def test_enrollment_tidak_memblokir_endpoint_lain(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def enroll_lambat(con, embedder, nama, harga_modal, foto_paths, **kw):
        time.sleep(KERJA)
        return db.add_product(con, nama, harga_modal, np.zeros(4, dtype=np.float32))

    monkeypatch.setattr("stoklens.enroll.enroll_product", enroll_lambat)
    app = create_app(db_path=dbp, embedder=object())

    t_enroll, t_get = asyncio.run(_absolut(
        app, "/products", {"fotos": ("a.jpg", _jpeg(), "image/jpeg")},
        data={"nama": "Indomie", "harga_modal": 3200}))

    assert t_enroll >= KERJA, "stub tidak terpakai — test ini tidak menguji apa pun"
    assert t_get < t_enroll, (
        f"GET selesai di {t_get:.2f}s, enrollment di {t_enroll:.2f}s — event loop terblokir")


def test_scan_video_tidak_memblokir_endpoint_lain(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.db")
    db.connect(dbp).close()

    def run_lambat(con, embedder, video_path, **kw):
        time.sleep(KERJA)
        return db.add_scan(con, video_ref=str(video_path))

    monkeypatch.setattr("stoklens.scan.run_scan", run_lambat)
    app = create_app(db_path=dbp, embedder=object())

    t_scan, t_get = asyncio.run(_absolut(
        app, "/scans", {"video": ("v.mp4", b"bukan-video-sungguhan", "video/mp4")}))

    assert t_scan >= KERJA, "stub tidak terpakai — test ini tidak menguji apa pun"
    assert t_get < t_scan, (
        f"GET selesai di {t_get:.2f}s, scan di {t_scan:.2f}s — event loop terblokir")
