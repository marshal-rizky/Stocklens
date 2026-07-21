"""Test UI "Belum dikenali" (enroll dari scan, Unit 4): section + sheet ditambahkan
ke report_view.js/app.css, dan halaman yang memakai report_view.js tetap render
normal. Tidak ada JS runner di repo ini — semua diuji lewat konten statis yang
disajikan TestClient, pola sama seperti test_webui.py (lihat test_static_tokens_css)."""
from fastapi.testclient import TestClient

from stoklens.api import create_app


def _client(tmp_path):
    dbp = str(tmp_path / "t.db")
    return TestClient(create_app(db_path=dbp))


def test_report_view_js_punya_section_belum_dikenali(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "Belum dikenali" in r.text
    assert "Ini barang apa?" in r.text


def test_report_view_js_panggil_endpoint_unknown_assign_produk_baru(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "/api/scans/" in r.text and "/unknown" in r.text
    assert "/api/unknown/" in r.text
    assert "/assign" in r.text
    assert "/produk-baru" in r.text


def test_report_view_js_sheet_pakai_helper_bersama_bukan_reimplementasi(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    # Harus pakai angka()/escapeHtml()/api()/toast() dari app.js sesuai house rule,
    # bukan bikin parser angka atau fetch-wrapper sendiri.
    assert "angka(" in r.text
    assert "escapeHtml(" in r.text
    assert 'api("/api/products")' in r.text


def test_report_view_js_field_error_pola_hidden(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    # Validasi harga_modal minimal Rp1 pakai pola field-error + .hidden, bukan toast.
    assert "sheet-error-harga-modal" in r.text
    assert 'classList.remove("hidden")' in r.text


def test_app_css_punya_grid_crop_dan_sheet(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/app.css")
    assert r.status_code == 200
    assert ".thumb-unknown" in r.text
    assert ".thumb-tanya" in r.text
    assert ".sheet-backdrop" in r.text
    assert ".sheet-panel" in r.text
    assert ".sheet-close" in r.text


def test_app_css_sheet_hormati_prefers_reduced_motion(tmp_path):
    client = _client(tmp_path)
    r = client.get("/static/app.css")
    assert r.status_code == 200
    idx = r.text.find(".sheet-backdrop {")
    assert idx != -1
    tail = r.text[idx:]
    assert "prefers-reduced-motion: reduce" in tail


def test_halaman_yang_pakai_report_view_masih_render(tmp_path):
    client = _client(tmp_path)
    for path in ("/ui/opname/foto", "/ui/opname/manual", "/ui/opname/video", "/ui/laporan/1"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "report_view.js" in r.text


def test_get_unknown_scan_kosong_untuk_scan_tak_ada(tmp_path):
    """Sanity check kontrak yang dipakai UI: scan tanpa crop unknown (termasuk
    scan_id yang tidak ada, mis. dari opname manual) balas 200 list kosong, bukan
    404 — supaya fetch diam-diam di renderReport tidak pernah salah expect error."""
    client = _client(tmp_path)
    r = client.get("/api/scans/999/unknown")
    assert r.status_code == 200
    assert r.json() == []
