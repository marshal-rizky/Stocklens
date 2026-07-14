"""Test fondasi UI mobile: routing /ui/*, static assets, redirect dari /."""
from fastapi.testclient import TestClient

from stoklens.api import create_app


def _client(tmp_path):
    dbp = str(tmp_path / "t.db")
    return TestClient(create_app(db_path=dbp))


def test_root_redirect_ke_beranda(tmp_path):
    client = _client(tmp_path)
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/ui/beranda"


def test_beranda_render_nav(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/beranda")
    assert r.status_code == 200
    assert "<nav" in r.text
    for label in ("Beranda", "Barang", "Opname", "Laporan"):
        assert label in r.text


def test_semua_halaman_ui_render(tmp_path):
    client = _client(tmp_path)
    for path in ("/ui/beranda", "/ui/barang", "/ui/opname", "/ui/laporan"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "<nav" in r.text


def test_static_tokens_css(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/tokens.css")
    assert r.status_code == 200
    assert "--primary:#2563EB" in r.text


def test_json_api_masih_jalan(tmp_path):
    client = _client(tmp_path)
    assert client.get("/api/products").status_code == 200


def test_beranda_punya_kpi_dan_peringatan(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/beranda")
    assert r.status_code == 200
    for id_ in ("kpi-nilai", "kpi-laba", "kpi-opname", "peringatan"):
        assert f'id="{id_}"' in r.text
