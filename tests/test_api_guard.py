"""Guard HTTP Basic yang dipasang saat app diekspos ke internet."""
from fastapi.testclient import TestClient

from stoklens.api import create_app


def _client(tmp_path, monkeypatch, sandi):
    if sandi is None:
        monkeypatch.delenv("STOKLENS_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("STOKLENS_PASSWORD", sandi)
    return TestClient(create_app(db_path=str(tmp_path / "t.db")))


def test_tanpa_env_app_tetap_polos(tmp_path, monkeypatch):
    """Dev lokal, docker compose, dan test lain tidak boleh ikut terkunci."""
    c = _client(tmp_path, monkeypatch, None)
    assert c.get("/api/products").status_code == 200


def test_sandi_diset_wajib_login(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, "rahasia")
    r = c.get("/api/products")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"].startswith("Basic")


def test_sandi_benar_lolos(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, "rahasia")
    assert c.get("/api/products", auth=("stoklens", "rahasia")).status_code == 200


def test_sandi_salah_ditolak(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, "rahasia")
    assert c.get("/api/products", auth=("stoklens", "salah")).status_code == 401


def test_halaman_ui_dan_static_ikut_dijaga(tmp_path, monkeypatch):
    """Guard harus menutup SEMUA, bukan cuma /api — halaman UI juga membocorkan data."""
    c = _client(tmp_path, monkeypatch, "rahasia")
    assert c.get("/ui/beranda").status_code == 401
    assert c.get("/static/app.js").status_code == 401
