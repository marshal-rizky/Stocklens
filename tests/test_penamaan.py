"""Hitungan opname ikut pindah ketika crop tak dikenali diberi nama.

Sebelum modul `penamaan` ada, memberi nama crop hanya menyentuh galeri produk.
Hitungannya tertinggal di baris "belum dikenali", dan karena `terapkan_opname`
hanya menulis baris ber-product_id, barang yang baru dinamai tidak pernah sampai
ke buku stok. Test di berkas ini mengunci perilaku barunya.
"""
import numpy as np

from stoklens import db, penamaan


def _vek(*nilai):
    return np.array(nilai, dtype=np.float32)


def _siap(tmp_path, qty_unknown=3):
    """Satu scan dengan sejumlah deteksi yang semuanya belum dikenali."""
    con = db.connect(str(tmp_path / "t.db"))
    sid = db.add_scan(con, video_ref="v.mp4")
    db.add_scan_item(con, sid, None, qty_unknown, 0.5)
    return con, sid


def test_hitungan_pindah_dari_unknown_ke_produk(tmp_path):
    con, sid = _siap(tmp_path, qty_unknown=3)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    cid = db.add_unknown_crop(con, sid, "a.jpg", _vek(0, 1, 0))

    hasil = penamaan.selesaikan_penamaan(con, cid, pid)

    assert hasil["dipindah"] == 1
    baris = {r["product_id"]: r["qty_terdeteksi"] for r in con.execute(
        "SELECT product_id, qty_terdeteksi FROM scan_items WHERE scan_id=?", (sid,))}
    assert baris[pid] == 1
    assert baris[None] == 2


def test_terapkan_opname_ikut_membawa_barang_yang_baru_dinamai(tmp_path):
    """Regresi inti: inilah gejala yang dilaporkan dari lapangan."""
    con, sid = _siap(tmp_path, qty_unknown=2)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    cid = db.add_unknown_crop(con, sid, "a.jpg", _vek(0, 1, 0))
    penamaan.selesaikan_penamaan(con, cid, pid)

    db.terapkan_opname(con, sid)

    assert db.get_stock_map(con)[pid] == 1


def test_crop_serupa_di_scan_yang_sama_ikut_tersapu(tmp_path):
    """Satu barang identik menghasilkan beberapa crop; user cuma menamai satu."""
    con, sid = _siap(tmp_path, qty_unknown=3)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    dinamai = db.add_unknown_crop(con, sid, "a.jpg", _vek(1, 0, 0))
    kembar = db.add_unknown_crop(con, sid, "b.jpg", _vek(1, 0, 0))
    db.add_unknown_crop(con, sid, "c.jpg", _vek(0, 0, 1))   # barang lain

    hasil = penamaan.selesaikan_penamaan(con, dinamai, pid)

    assert hasil["dipindah"] == 2
    assert hasil["ikut_terbawa"] == [kembar]
    baris = {r["product_id"]: r["qty_terdeteksi"] for r in con.execute(
        "SELECT product_id, qty_terdeteksi FROM scan_items WHERE scan_id=?", (sid,))}
    assert baris[pid] == 2
    assert baris[None] == 1


def test_crop_milik_produk_lain_tidak_ikut_tersapu(tmp_path):
    """Penyapuan mencocokkan ke SEMUA produk, bukan cuma yang barusan dinamai."""
    con, sid = _siap(tmp_path, qty_unknown=2)
    teh = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    kopi = db.add_product(con, "Kopi", 2000, _vek(0, 1, 0))
    cid = db.add_unknown_crop(con, sid, "a.jpg", _vek(1, 0, 0))
    db.add_unknown_crop(con, sid, "b.jpg", _vek(0, 1, 0))   # jelas milik kopi

    hasil = penamaan.selesaikan_penamaan(con, cid, teh)

    assert hasil["ikut_terbawa"] == []
    sisa = db.list_unknown_crops(con, scan_id=sid, hanya_belum=True)
    assert len(sisa) == 1
    assert db.get_stock_map(con).get(kopi) is None


def test_scan_yang_sudah_diterapkan_tidak_berubah_hitungannya(tmp_path):
    """Laporan yang sudah dibukukan harus tetap sama dengan yang dibukukan."""
    con, sid = _siap(tmp_path, qty_unknown=3)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    db.terapkan_opname(con, sid)
    cid = db.add_unknown_crop(con, sid, "a.jpg", _vek(1, 0, 0))

    hasil = penamaan.selesaikan_penamaan(con, cid, pid)

    assert hasil["dipindah"] == 0
    baris = {r["product_id"]: r["qty_terdeteksi"] for r in con.execute(
        "SELECT product_id, qty_terdeteksi FROM scan_items WHERE scan_id=?", (sid,))}
    assert baris[None] == 3
    # Penamaannya sendiri tetap berlaku untuk scan berikutnya.
    assert db.get_unknown_crop(con, cid)["product_id"] == pid


def test_pindah_berhenti_saat_baris_unknown_habis(tmp_path):
    """Crop tersimpan bisa lebih banyak dari hitungan unknown (cap maks_unknown)."""
    con, sid = _siap(tmp_path, qty_unknown=1)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    a = db.add_unknown_crop(con, sid, "a.jpg", _vek(1, 0, 0))
    db.add_unknown_crop(con, sid, "b.jpg", _vek(1, 0, 0))

    hasil = penamaan.selesaikan_penamaan(con, a, pid)

    assert hasil["dipindah"] == 1
    kosong = con.execute(
        "SELECT COUNT(*) FROM scan_items WHERE scan_id=? AND product_id IS NULL",
        (sid,)).fetchone()[0]
    assert kosong == 0, "baris unknown yang habis harus dibuang, bukan disisakan 0"


def test_pindahkan_hitungan_tanpa_baris_unknown_aman(tmp_path):
    con = db.connect(str(tmp_path / "t.db"))
    sid = db.add_scan(con, video_ref="v.mp4")
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))

    assert db.pindahkan_hitungan_unknown(con, sid, pid) == 0


def test_confidence_produk_hasil_penamaan_kosong(tmp_path):
    """Hitungan dari mata manusia tidak boleh menyamar jadi keyakinan model."""
    con, sid = _siap(tmp_path, qty_unknown=2)
    pid = db.add_product(con, "Teh pucuk", 3000, _vek(1, 0, 0))
    cid = db.add_unknown_crop(con, sid, "a.jpg", _vek(1, 0, 0))

    penamaan.selesaikan_penamaan(con, cid, pid)

    conf = con.execute(
        "SELECT confidence_avg FROM scan_items WHERE scan_id=? AND product_id=?",
        (sid, pid)).fetchone()[0]
    assert conf is None
