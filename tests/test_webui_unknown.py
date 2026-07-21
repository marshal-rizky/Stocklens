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


def test_report_view_js_field_error_nama_wajib_diisi(tmp_path):
    """Review fix Minor #5: nama kosong/spasi-saja harus dapat field-error, bukan
    gagal diam-diam kayak sebelumnya."""
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "sheet-error-nama" in r.text
    assert "Nama wajib diisi" in r.text


def test_report_view_js_generasi_cegah_race_sheet_dipakai_ulang(tmp_path):
    """Review fix Important #1: request assign/produk-baru/muat-produk yang masih
    in-flight harus di-no-op kalau sheet sudah dipakai ulang untuk crop lain,
    lewat penanda generasi yang ditangkap SEBELUM await."""
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "sheetGenerasi" in r.text
    assert "const generasi = sheetGenerasi;" in r.text
    assert "const generasi = ++sheetGenerasi;" in r.text
    assert "generasi !== sheetGenerasi" in r.text


def test_report_view_js_muat_belum_dikenali_bedakan_gagal_vs_kosong(tmp_path):
    """Review fix Important #2: kegagalan fetch (non-2xx / network error) dicatat
    console.error, dibedakan dari list yang memang kosong."""
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "console.error" in r.text


def test_report_view_js_sheet_punya_focus_trap_dan_restore(tmp_path):
    """Review fix Important #3: role=dialog aria-modal=true sekarang dibarengi
    focus trap (Tab/Shift+Tab siklus) + kembalikan fokus ke pemicu saat tutup."""
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "sheetKeydownHandler" in r.text
    assert "daftarFokusableSheet" in r.text
    assert "sheetPemicu" in r.text
    assert '.focus()' in r.text


def test_report_view_js_double_submit_guard_pilih_produk_dan_tap_crop(tmp_path):
    """Review fix Important #4 + Minor #7: tombol daftar produk di-disable selama
    request assign, dan tombol 'Ini barang apa?' di-disable saat sheet dibuka."""
    client = _client(tmp_path)
    r = client.get("/static/report_view.js")
    assert r.status_code == 200
    assert "tombolProduk.forEach((b) => (b.disabled = true))" in r.text
    assert "btn.disabled = true;" in r.text


def test_get_unknown_scan_kosong_untuk_scan_tak_ada(tmp_path):
    """Sanity check kontrak yang dipakai UI: scan tanpa crop unknown (termasuk
    scan_id yang tidak ada, mis. dari opname manual) balas 200 list kosong, bukan
    404 — supaya fetch diam-diam di renderReport tidak pernah salah expect error."""
    client = _client(tmp_path)
    r = client.get("/api/scans/999/unknown")
    assert r.status_code == 200
    assert r.json() == []
