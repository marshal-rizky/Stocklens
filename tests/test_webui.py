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
    assert "beranda.js" in r.text
    assert 'data-slot="angka"' in r.text


def test_barang_punya_search_daftar_fab(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/barang")
    assert r.status_code == 200
    assert 'type="search"' in r.text
    assert 'id="daftar-barang"' in r.text
    assert 'href="/ui/barang/baru"' in r.text
    assert "barang.js" in r.text


def test_barang_baru_punya_form_dan_input_kamera(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/barang/baru")
    assert r.status_code == 200
    assert "Nama" in r.text
    assert "Harga modal" in r.text
    assert 'capture="environment"' in r.text
    assert "barang_baru.js" in r.text


def test_barang_detail_punya_container_dan_skrip(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/barang/5")
    assert r.status_code == 200
    assert 'data-product-id="5"' in r.text
    assert "barang_detail.js" in r.text


def test_opname_hub_punya_3_link_mode(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/opname")
    assert r.status_code == 200
    for path in ("/ui/opname/foto", "/ui/opname/manual", "/ui/opname/video"):
        assert f'href="{path}"' in r.text


def test_opname_manual_punya_container_checklist_dan_skrip(tmp_path):
    client = _client(tmp_path)
    r = client.get("/ui/opname/manual")
    assert r.status_code == 200
    assert 'id="daftar-checklist"' in r.text
    assert "opname_manual.js" in r.text
    assert "report_view.js" in r.text


