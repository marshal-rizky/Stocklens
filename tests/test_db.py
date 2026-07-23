import sqlite3

import numpy as np
import pytest

from stoklens import db


def _con():
    return db.connect(":memory:")


def test_add_dan_baca_product():
    con = _con()
    emb = np.arange(4, dtype=np.float32)
    pid = db.add_product(con, "Indomie Goreng", 3200, emb, harga_jual=3500)
    rows = db.all_products(con)
    assert len(rows) == 1
    assert rows[0]["id"] == pid
    assert rows[0]["nama"] == "Indomie Goreng"
    assert np.allclose(rows[0]["embedding"], emb)


def test_stock_ledger_ambil_terbaru():
    con = _con()
    pid = db.add_product(con, "Minyak 1L", 15000, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 40)
    db.set_stock(con, pid, 37)
    assert db.get_stock_map(con) == {pid: 37}


def test_scan_dan_report_rows():
    con = _con()
    pid = db.add_product(con, "Gula 1kg", 12000, np.zeros(4, dtype=np.float32))
    db.set_stock(con, pid, 10)
    sid = db.add_scan(con, video_ref="rak1.mp4", lokasi_rak="Rak 1")
    db.add_scan_item(con, sid, pid, qty_terdeteksi=8, confidence_avg=0.91,
                     expired_terdekat="2026-08-01", qty_expired=2)
    rows = db.get_report_rows(con, sid)
    assert rows == [{
        "nama": "Gula 1kg", "harga_modal": 12000, "qty_tercatat": 10,
        "qty_terdeteksi": 8, "qty_expired": 2,
        "expired_terdekat": "2026-08-01", "confidence_avg": 0.91,
    }]


def test_list_scans_urutan_terbaru_dulu():
    con = _con()
    sid1 = db.add_scan(con, lokasi_rak="Rak 1", tipe="manual")
    sid2 = db.add_scan(con, lokasi_rak="Rak 2", tipe="foto")
    rows = db.list_scans(con)
    assert [r["id"] for r in rows] == [sid2, sid1]
    assert rows[0]["lokasi_rak"] == "Rak 2"
    assert rows[0]["tipe"] == "foto"


def test_get_scan_items_hanya_yang_punya_product_id():
    con = _con()
    pid = db.add_product(con, "Gula 1kg", 12000, np.zeros(4, dtype=np.float32))
    sid = db.add_scan(con)
    db.add_scan_item(con, sid, pid, qty_terdeteksi=8)
    db.add_scan_item(con, sid, None, qty_terdeteksi=1)  # unknown, tanpa product_id
    items = db.get_scan_items(con, sid)
    assert items == [{"product_id": pid, "qty_terdeteksi": 8}]


# ---- Terapkan opname ke ledger (helper bersama, transaksi atomik) ----

def test_terapkan_opname_tulis_ledger_dan_tandai_scan():
    con = _con()
    p1 = db.add_product(con, "Gula 1kg", 12000, np.zeros(2, dtype=np.float32))
    p2 = db.add_product(con, "Indomie", 3200, np.zeros(2, dtype=np.float32))
    db.set_stock(con, p1, 10)
    db.set_stock(con, p2, 20)
    sid = db.add_scan(con, lokasi_rak="Rak 1", tipe="manual")
    db.add_scan_item(con, sid, p1, qty_terdeteksi=8)
    db.add_scan_item(con, sid, p2, qty_terdeteksi=25)
    db.add_scan_item(con, sid, None, qty_terdeteksi=3)  # unknown, jangan ke ledger

    assert db.terapkan_opname(con, sid) == 2            # unknown tidak dihitung

    assert db.get_stock_map(con) == {p1: 8, p2: 25}
    baris = db.get_ledger(con, p1)[0]
    assert baris["qty_tercatat"] == 8
    assert baris["sumber"] == "opname"
    assert baris["alasan"] == f"opname #{sid}"
    assert len(db.get_ledger(con, p1)) == 2             # satu baris baru saja
    assert db.get_scan(con, sid)["terapkan_pada"] is not None


class _KoneksiGagalSaatUpdateScan(sqlite3.Connection):
    """Connection yang meledak persis di UPDATE scans (setelah INSERT ledger).

    sqlite3.Connection tidak punya __dict__, jadi tidak bisa di-monkeypatch per
    instance — subclass lewat argumen factory= adalah cara bersihnya.
    """

    def execute(self, sql, *args):
        if sql.lstrip().upper().startswith("UPDATE SCANS"):
            raise sqlite3.OperationalError("simulasi gagal di tengah terapkan")
        return super().execute(sql, *args)


def test_terapkan_opname_atomik_rollback_saat_gagal(tmp_path):
    path = str(tmp_path / "atomik.db")
    # Lewat db.connect() (bukan sqlite3.connect mentah) supaya test ini benar-benar
    # memakai konfigurasi koneksi produksi — termasuk isolation_level="" yang jadi
    # sandaran atomicity-nya.
    con = db.connect(path, factory=_KoneksiGagalSaatUpdateScan)
    pid = db.add_product(con, "Gula 1kg", 12000, np.zeros(2, dtype=np.float32))
    db.set_stock(con, pid, 10)
    sid = db.add_scan(con, lokasi_rak="Rak 1", tipe="manual")
    db.add_scan_item(con, sid, pid, qty_terdeteksi=8)

    with pytest.raises(sqlite3.OperationalError):
        db.terapkan_opname(con, sid)

    # INSERT ledger sudah sempat jalan sebelum UPDATE meledak — harus di-rollback,
    # jadi tidak ada ledger separuh terisi dan scan tetap belum ditandai.
    assert db.get_stock_map(con) == {pid: 10}
    assert len(db.get_ledger(con, pid)) == 1
    assert db.get_scan(con, sid)["terapkan_pada"] is None

    # dan benar-benar tidak ada yang ter-commit ke file DB
    lain = db.connect(path)
    assert len(db.get_ledger(lain, pid)) == 1
    assert db.get_scan(lain, sid)["terapkan_pada"] is None


def test_terapkan_opname_tanpa_item_tetap_menandai_scan():
    # Scan yang semua item-nya belum dikenali (product_id NULL) — atau tanpa item
    # sama sekali — tidak menulis satu pun baris ledger, TAPI tetap ditandai
    # applied: scan-nya memang sudah diproses. Kalau tidak ditandai, scan itu
    # selamanya bisa "diterapkan" lagi dan guard terapkan-ganda jadi bocor.
    con = _con()
    pid = db.add_product(con, "Gula 1kg", 12000, np.zeros(2, dtype=np.float32))
    db.set_stock(con, pid, 10)
    sid = db.add_scan(con, tipe="manual")
    db.add_scan_item(con, sid, None, qty_terdeteksi=3)   # unknown, tanpa produk

    assert db.terapkan_opname(con, sid) == 0
    assert db.get_stock_map(con) == {pid: 10}            # ledger tidak tersentuh
    assert db.get_scan(con, sid)["terapkan_pada"] is not None

    with pytest.raises(ValueError):                      # terapkan kedua ditolak
        db.terapkan_opname(con, sid)


def test_terapkan_opname_scan_tidak_ada_raise():
    con = _con()
    with pytest.raises(ValueError):
        db.terapkan_opname(con, 999)


def test_terapkan_opname_dua_koneksi_hanya_satu_yang_menang(tmp_path):
    # Balapan terapkan-ganda: dua koneksi (mis. dua request yang saling tumpang
    # tindih) menerapkan scan yang sama. Compare-and-set bikin yang kedua kalah,
    # tanpa meninggalkan baris ledger duplikat.
    path = str(tmp_path / "balapan.db")
    a = db.connect(path)
    pid = db.add_product(a, "Gula 1kg", 12000, np.zeros(2, dtype=np.float32))
    db.set_stock(a, pid, 10)
    sid = db.add_scan(a, tipe="manual")
    db.add_scan_item(a, sid, pid, qty_terdeteksi=8)

    b = db.connect(path)
    assert db.terapkan_opname(a, sid) == 1
    with pytest.raises(ValueError):
        db.terapkan_opname(b, sid)

    # satu baris awal (set_stock) + satu baris opname saja, bukan dua opname
    ledger = db.get_ledger(db.connect(path), pid)
    assert len(ledger) == 2
    assert [r["sumber"] for r in ledger] == ["opname", "manual"]


# ---- Galeri embedding (enroll dari scan) ----

def test_all_products_kembalikan_galeri_embeddings():
    con = _con()
    pid = db.add_product(con, "Indomie", 3200, np.array([1, 0], dtype=np.float32))
    # awalnya galeri hanya berisi embedding enrollment
    p = db.all_products(con, with_gallery=True)[0]
    assert len(p["embeddings"]) == 1
    assert np.allclose(p["embeddings"][0], [1, 0])

    db.add_product_embedding(con, pid, np.array([0, 1], dtype=np.float32),
                             sumber="scan")
    p = db.all_products(con, with_gallery=True)[0]
    assert len(p["embeddings"]) == 2
    assert np.allclose(p["embeddings"][1], [0, 1])


def test_all_products_tanpa_with_gallery_tidak_bawa_embeddings():
    con = _con()
    pid = db.add_product(con, "Indomie", 3200, np.array([1, 0], dtype=np.float32))
    db.add_product_embedding(con, pid, np.array([0, 1], dtype=np.float32))
    p = db.all_products(con)[0]
    assert "embeddings" not in p        # galeri opt-in, jangan dikirim sia-sia
    assert np.allclose(p["embedding"], [1, 0])   # embedding tunggal tetap ada


def test_all_products_galeri_dikelompokkan_per_produk():
    con = _con()
    p1 = db.add_product(con, "Indomie", 3200, np.array([1, 0], dtype=np.float32))
    p2 = db.add_product(con, "Gula", 12000, np.array([0, 1], dtype=np.float32))
    db.add_product_embedding(con, p1, np.array([0.9, 0.1], dtype=np.float32))
    db.add_product_embedding(con, p2, np.array([0.1, 0.9], dtype=np.float32))
    db.add_product_embedding(con, p1, np.array([0.8, 0.2], dtype=np.float32))

    a, b = db.all_products(con, with_gallery=True)
    # galeri satu query harus tetap masuk ke produk yang benar, urut id
    assert len(a["embeddings"]) == 3 and len(b["embeddings"]) == 2
    assert np.allclose(a["embeddings"][1], [0.9, 0.1])
    assert np.allclose(a["embeddings"][2], [0.8, 0.2])
    assert np.allclose(b["embeddings"][1], [0.1, 0.9])


def test_count_product_embeddings():
    con = _con()
    p1 = db.add_product(con, "Indomie", 3200, np.array([1, 0], dtype=np.float32))
    p2 = db.add_product(con, "Gula", 12000, np.array([0, 1], dtype=np.float32))
    assert db.count_product_embeddings(con, p1) == 0   # enrollment tidak dihitung
    db.add_product_embedding(con, p1, np.array([0, 1], dtype=np.float32))
    db.add_product_embedding(con, p1, np.array([1, 1], dtype=np.float32))
    assert db.count_product_embeddings(con, p1) == 2
    assert db.count_product_embeddings(con, p2) == 0


def test_unknown_crop_simpan_daftar_dan_resolve():
    con = _con()
    pid = db.add_product(con, "Indomie", 3200, np.array([1, 0], dtype=np.float32))
    sid = db.add_scan(con, tipe="foto")
    cid = db.add_unknown_crop(con, sid, "data/crops/1.jpg",
                              np.array([0.9, 0.1], dtype=np.float32))

    belum = db.list_unknown_crops(con, sid)
    assert len(belum) == 1
    assert belum[0]["id"] == cid
    assert belum[0]["crop_path"] == "data/crops/1.jpg"

    assert db.resolve_unknown_crop(con, cid, pid) == 1    # 1 baris kena update
    assert db.resolve_unknown_crop(con, 999, pid) == 0    # crop_id tidak ada
    assert db.list_unknown_crops(con, sid) == []          # sudah tidak menggantung
    assert len(db.list_unknown_crops(con, sid, hanya_belum=False)) == 1


def test_get_unknown_crop_bawa_embedding():
    con = _con()
    sid = db.add_scan(con)
    cid = db.add_unknown_crop(con, sid, "x.jpg", np.array([0.5, 0.5], dtype=np.float32))
    c = db.get_unknown_crop(con, cid)
    assert np.allclose(c["embedding"], [0.5, 0.5])
    assert db.get_unknown_crop(con, 999) is None
