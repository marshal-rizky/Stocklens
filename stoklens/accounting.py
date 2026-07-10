"""Fungsi akuntansi stok dasar (murni — tanpa DB, gampang dites).

Konvensi:
- products: list dict minimal berisi id, nama, harga_modal, harga_jual, stok_minimum
- stock_map: {product_id: qty_tercatat} dari db.get_stock_map(); produk yang belum
  pernah punya entri ledger dianggap qty 0
"""


def margin_pct(harga_modal, harga_jual):
    """Margin kotor % dari harga modal; None kalau data tidak lengkap."""
    if not harga_jual or not harga_modal or harga_modal <= 0:
        return None
    return round((harga_jual - harga_modal) / harga_modal * 100, 1)


def nilai_stok(products, stock_map):
    """Total nilai stok pada harga modal (Rp)."""
    return sum(stock_map.get(p["id"], 0) * p["harga_modal"] for p in products)


def potensi_laba(products, stock_map):
    """Potensi laba kotor kalau semua stok terjual (hanya produk ber-harga_jual)."""
    return sum(
        stock_map.get(p["id"], 0) * (p["harga_jual"] - p["harga_modal"])
        for p in products
        if p.get("harga_jual")
    )


def stok_menipis(products, stock_map):
    """Produk dengan qty <= stok_minimum (hanya yang set minimum > 0)."""
    out = []
    for p in products:
        minimum = p.get("stok_minimum") or 0
        qty = stock_map.get(p["id"], 0)
        if minimum > 0 and qty <= minimum:
            out.append({"id": p["id"], "nama": p["nama"], "qty": qty,
                        "stok_minimum": minimum})
    return out


def apply_adjustment(qty_sekarang, delta):
    """Qty baru setelah penyesuaian manual; stok tidak boleh jadi negatif."""
    baru = qty_sekarang + delta
    if baru < 0:
        raise ValueError(
            f"Penyesuaian {delta:+d} membuat stok negatif (sekarang {qty_sekarang})"
        )
    return baru
