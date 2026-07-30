"""Laporan selisih fisik vs tercatat, dinilai dalam rupiah."""


def build_report(rows, tidak_terdeteksi=()):
    """rows: dict dengan nama, harga_modal, qty_tercatat, qty_terdeteksi, qty_expired.

    Shrinkage hanya dihitung untuk selisih negatif (barang kurang).

    tidak_terdeteksi: produk berstok yang TIDAK muncul sama sekali di scan
    (lihat db.get_tidak_terdeteksi). Ditumpangkan apa adanya ke output supaya
    user melihatnya — sebelum ini barang seperti itu hilang total dari laporan,
    padahal "barang habis tanpa tercatat" justru kasus paling penting bagi
    pemilik warung.

    Nilainya SENGAJA tidak masuk `total_shrinkage_rp`. Scan satu rak tidak
    melihat rak lain, jadi menganggap semua yang tak terdeteksi sebagai hilang
    akan melaporkan seluruh barang rak lain sebagai shrinkage — angka salah
    yang disajikan dengan percaya diri lebih buruk daripada angka yang belum
    dihitung. User yang menegaskan mana yang benar-benar habis, lewat
    penyesuaian stok.
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
    hilang = [dict(h) for h in tidak_terdeteksi]
    return {
        "items": items,
        "total_nilai_rp": total_nilai,
        "total_shrinkage_rp": total_shrink,
        "total_rugi_expired_rp": total_rugi,
        "tidak_terdeteksi": hilang,
        "total_tidak_terdeteksi_rp": sum(h["nilai_rp"] for h in hilang),
    }
