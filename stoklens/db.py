"""SQLite: schema + CRUD. Embedding disimpan sebagai BLOB float32."""
import json
import sqlite3

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY,
  nama TEXT NOT NULL UNIQUE,
  harga_modal INTEGER NOT NULL,
  harga_jual INTEGER,
  stok_minimum INTEGER DEFAULT 0,
  embedding BLOB NOT NULL,
  foto_refs TEXT NOT NULL DEFAULT '[]',
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS scans(
  id INTEGER PRIMARY KEY,
  tanggal TEXT DEFAULT (datetime('now')),
  lokasi_rak TEXT,
  video_ref TEXT,
  tipe TEXT DEFAULT 'video',
  status TEXT DEFAULT 'selesai',
  terapkan_pada TEXT
);
CREATE TABLE IF NOT EXISTS scan_items(
  id INTEGER PRIMARY KEY,
  scan_id INTEGER NOT NULL REFERENCES scans(id),
  product_id INTEGER REFERENCES products(id),
  qty_terdeteksi INTEGER NOT NULL,
  confidence_avg REAL,
  expired_terdekat TEXT,
  qty_expired INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS stock_ledger(
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  qty_tercatat INTEGER NOT NULL,
  sumber TEXT DEFAULT 'manual',
  alasan TEXT,
  tanggal_update TEXT DEFAULT (datetime('now'))
);
"""

# Migrasi kolom untuk DB lama (SCHEMA pakai IF NOT EXISTS, jadi tabel lama
# tidak otomatis dapat kolom baru). Aman dijalankan berulang.
_MIGRATIONS = [
    "ALTER TABLE products ADD COLUMN stok_minimum INTEGER DEFAULT 0",
    "ALTER TABLE scans ADD COLUMN tipe TEXT DEFAULT 'video'",
    "ALTER TABLE stock_ledger ADD COLUMN alasan TEXT",
    "ALTER TABLE scans ADD COLUMN terapkan_pada TEXT",
]


def connect(path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for m in _MIGRATIONS:
        try:
            con.execute(m)
        except sqlite3.OperationalError:
            pass  # kolom sudah ada
    return con


def add_product(con, nama, harga_modal, embedding, harga_jual=None, foto_refs=()):
    blob = np.asarray(embedding, dtype=np.float32).tobytes()
    cur = con.execute(
        "INSERT INTO products(nama, harga_modal, harga_jual, embedding, foto_refs)"
        " VALUES(?,?,?,?,?)",
        (nama, harga_modal, harga_jual, blob, json.dumps([str(f) for f in foto_refs])),
    )
    con.commit()
    return cur.lastrowid


def all_products(con):
    rows = con.execute("SELECT * FROM products ORDER BY id").fetchall()
    return [
        dict(r) | {"embedding": np.frombuffer(r["embedding"], dtype=np.float32)}
        for r in rows
    ]


def set_stock(con, product_id, qty, sumber="manual", alasan=None):
    con.execute(
        "INSERT INTO stock_ledger(product_id, qty_tercatat, sumber, alasan)"
        " VALUES(?,?,?,?)",
        (product_id, qty, sumber, alasan),
    )
    con.commit()


def get_product(con, product_id):
    r = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d.pop("embedding", None)  # BLOB tidak untuk API
    return d


# Kolom yang boleh diedit user via API — embedding dkk dikelola sistem.
EDITABLE_FIELDS = {"nama", "harga_modal", "harga_jual", "stok_minimum"}


def update_product(con, product_id, **fields):
    bad = set(fields) - EDITABLE_FIELDS
    if bad:
        raise ValueError(f"Field tidak boleh diedit: {sorted(bad)}")
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    con.execute(f"UPDATE products SET {cols} WHERE id=?",
                (*fields.values(), product_id))
    con.commit()


def get_ledger(con, product_id, limit=50):
    rows = con.execute(
        "SELECT qty_tercatat, sumber, alasan, tanggal_update FROM stock_ledger"
        " WHERE product_id=? ORDER BY id DESC LIMIT ?",
        (product_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stock_map(con):
    """{product_id: qty_tercatat terbaru}"""
    rows = con.execute(
        "SELECT product_id, qty_tercatat FROM stock_ledger"
        " WHERE id IN (SELECT MAX(id) FROM stock_ledger GROUP BY product_id)"
    ).fetchall()
    return {r["product_id"]: r["qty_tercatat"] for r in rows}


def add_scan(con, video_ref=None, lokasi_rak=None, tipe="video"):
    cur = con.execute(
        "INSERT INTO scans(video_ref, lokasi_rak, tipe) VALUES(?,?,?)",
        (video_ref, lokasi_rak, tipe),
    )
    con.commit()
    return cur.lastrowid


def add_scan_item(con, scan_id, product_id, qty_terdeteksi, confidence_avg=None,
                  expired_terdekat=None, qty_expired=0):
    con.execute(
        "INSERT INTO scan_items(scan_id, product_id, qty_terdeteksi, confidence_avg,"
        " expired_terdekat, qty_expired) VALUES(?,?,?,?,?,?)",
        (scan_id, product_id, qty_terdeteksi, confidence_avg, expired_terdekat, qty_expired),
    )
    con.commit()


def get_report_rows(con, scan_id):
    """Baris siap dipakai report.build_report (hanya item yang match produk)."""
    stock = get_stock_map(con)
    rows = con.execute(
        "SELECT p.id AS pid, p.nama, p.harga_modal, si.qty_terdeteksi,"
        " si.confidence_avg, si.expired_terdekat, si.qty_expired"
        " FROM scan_items si JOIN products p ON p.id = si.product_id"
        " WHERE si.scan_id = ? ORDER BY p.nama",
        (scan_id,),
    ).fetchall()
    return [
        {
            "nama": r["nama"], "harga_modal": r["harga_modal"],
            "qty_tercatat": stock.get(r["pid"], 0),
            "qty_terdeteksi": r["qty_terdeteksi"], "qty_expired": r["qty_expired"],
            "expired_terdekat": r["expired_terdekat"],
            "confidence_avg": r["confidence_avg"],
        }
        for r in rows
    ]


def latest_scan_id(con):
    row = con.execute("SELECT MAX(id) AS mid FROM scans").fetchone()
    return row["mid"]


def get_scan(con, scan_id):
    r = con.execute(
        "SELECT id, tanggal, lokasi_rak, tipe, status, terapkan_pada"
        " FROM scans WHERE id=?",
        (scan_id,),
    ).fetchone()
    return dict(r) if r else None


def list_scans(con):
    """Semua scan, terbaru dulu."""
    rows = con.execute(
        "SELECT id, tanggal, lokasi_rak, tipe, status, terapkan_pada"
        " FROM scans ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def mark_scan_applied(con, scan_id):
    """Tandai scan sudah diterapkan ke ledger (guard terapkan ganda)."""
    con.execute(
        "UPDATE scans SET terapkan_pada = datetime('now') WHERE id=?",
        (scan_id,),
    )
    con.commit()


def get_scan_items(con, scan_id):
    """scan_items yang punya product_id (bukan None) — untuk terapkan ke ledger."""
    rows = con.execute(
        "SELECT product_id, qty_terdeteksi FROM scan_items"
        " WHERE scan_id=? AND product_id IS NOT NULL",
        (scan_id,),
    ).fetchall()
    return [dict(r) for r in rows]
