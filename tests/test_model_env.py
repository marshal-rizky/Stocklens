"""Bobot detektor bisa diarahkan lewat env STOKLENS_MODEL.

Tanpa ini `stoklens/photo.py` dan `stoklens/scan.py` mem-hardcode `yolo11n.pt`,
yaitu model COCO bawaan ultralytics — kelasnya orang/mobil/anjing, bukan produk
retail. Terukur pada foto rak warung asli: yolo11n memberi 0 kotak, sedangkan
model pre-train SKU-110K memberi 33 kotak pada foto yang sama. Jadi tanpa jalan
untuk menukar bobot, aplikasi yang dijalankan apa adanya tidak menemukan apa pun
dan uji lapangan jadi menyesatkan.

Nama env-nya sengaja diuji di KEDUA modul: nilainya di-inline di dua tempat
(mengikuti pola STOKLENS_DB di api.py), jadi salah ketik di salah satunya tidak
akan ketahuan tanpa test ini.
"""
import pytest

from stoklens import db, photo, scan


class _Ditangkap(Exception):
    """Dilempar fake YOLO supaya pipeline berhenti tepat setelah bobot dimuat."""


@pytest.fixture
def rekam_bobot(monkeypatch):
    """Catat path yang diteruskan ke YOLO(), lalu hentikan eksekusi."""
    dipakai = []

    class FakeYOLO:
        def __init__(self, path, *a, **kw):
            dipakai.append(path)
            raise _Ditangkap

    monkeypatch.setattr("ultralytics.YOLO", FakeYOLO)
    return dipakai


@pytest.fixture
def panggil(request, tmp_path):
    """Panggil jalur photo atau scan sampai tepat setelah bobot dimuat.

    run_scan membaca produk dari DB sebelum memuat model, jadi ia butuh koneksi
    sungguhan — bukan None.
    """
    if request.param == "photo":
        return lambda **kw: photo._yolo_detector(**kw)
    con = db.connect(str(tmp_path / "t.db"))
    return lambda **kw: scan.run_scan(con, None, "tak-dipakai.mp4", **kw)


@pytest.mark.parametrize("panggil", ["photo", "scan"], indirect=True)
def test_default_tetap_yolo11n(rekam_bobot, monkeypatch, panggil):
    monkeypatch.delenv("STOKLENS_MODEL", raising=False)
    with pytest.raises(_Ditangkap):
        panggil()
    assert rekam_bobot == ["yolo11n.pt"]


@pytest.mark.parametrize("panggil", ["photo", "scan"], indirect=True)
def test_env_menentukan_bobot(rekam_bobot, monkeypatch, panggil):
    monkeypatch.setenv("STOKLENS_MODEL", r"C:\bobot\best.pt")
    with pytest.raises(_Ditangkap):
        panggil()
    assert rekam_bobot == [r"C:\bobot\best.pt"]


@pytest.mark.parametrize("panggil", ["photo", "scan"], indirect=True)
def test_argumen_eksplisit_menang_atas_env(rekam_bobot, monkeypatch, panggil):
    """Sama seperti db_path di api.py: env tidak boleh mengganggu pemanggil
    yang sudah menyebut bobotnya sendiri (dipakai test lain dan skrip demo)."""
    monkeypatch.setenv("STOKLENS_MODEL", "harusnya-diabaikan.pt")
    with pytest.raises(_Ditangkap):
        panggil(model_path="eksplisit.pt")
    assert rekam_bobot == ["eksplisit.pt"]
