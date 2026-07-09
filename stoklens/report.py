"""Laporan selisih fisik vs tercatat, dinilai dalam rupiah."""


def build_report(rows):
    """rows: dict dengan nama, harga_modal, qty_tercatat, qty_terdeteksi, qty_expired.

    Shrinkage hanya dihitung untuk selisih negatif (barang kurang).
    """
    items = []
    total_nilai = total_shrink = total_rugi = 0
    for r in rows:
        selisih = r["qty_terdeteksi"] - r["qty_tercatat"]
        shrink_rp = -selisih * r["harga_modal"] if selisih < 0 else 0
        rugi_rp = r.get("qty_expired", 0) * r["harga_modal"]
        nilai_rp = r["qty_terdeteksi"] * r["harga_modal"]
        items.append(dict(r) | {
            "selisih": selisih, "shrinkage_rp": shrink_rp,
            "rugi_expired_rp": rugi_rp, "nilai_stok_rp": nilai_rp,
        })
        total_nilai += nilai_rp
        total_shrink += shrink_rp
        total_rugi += rugi_rp
    return {
        "items": items,
        "total_nilai_rp": total_nilai,
        "total_shrinkage_rp": total_shrink,
        "total_rugi_expired_rp": total_rugi,
    }
