"""Apa yang terjadi pada hasil opname ketika pengguna memberi nama satu crop.

MASALAH YANG DISELESAIKAN MODUL INI
-----------------------------------
Memberi nama crop tak dikenali dulunya hanya menyentuh galeri produk: crop
ditandai sudah di-resolve, embeddingnya masuk galeri, dan scan berikutnya jadi
mengenali barang itu. Yang TIDAK ikut berubah adalah hitungan scan yang sedang
dilihat. Barangnya tetap duduk di baris "belum dikenali", dan karena
`db.terapkan_opname()` hanya menulis baris yang punya product_id, barang yang
baru saja dinamai tidak pernah sampai ke buku stok.

Dari sisi pengguna gejalanya persis seperti yang dilaporkan saat uji: produk
baru muncul di katalog dengan stok awal saja, sementara barang yang tadi
dihitung di rak menguap.

DUA HAL YANG DIKERJAKAN DI SINI
-------------------------------
1. Hitungan satu crop dipindah dari "belum dikenali" ke produknya.
2. Sisa crop di scan yang sama dicocokkan ulang. Barang identik di rak
   menghasilkan beberapa crop terpisah, dan pengguna hanya menamai salah
   satunya; tanpa penyapuan ini yang lain tetap tertinggal sebagai "belum
   dikenali" padahal jawabannya sudah diketahui.

Penyapuan ulang murah: embedding tiap crop sudah tersimpan di baris
`unknown_crops`, jadi yang dikerjakan cuma cosine terhadap galeri. TIDAK ada
CLIP, tidak ada torch, dan modul ini bisa diuji tanpa keduanya.

Crop yang tersapu TIDAK ikut masuk galeri produk. Yang masuk galeri hanya crop
yang benar-benar ditunjuk manusia. Kalau tebakan mesin ikut dimasukkan, galeri
tumbuh dari tebakannya sendiri dan kesalahan pertama akan mengunci dirinya.
"""
from . import db
from .matcher import AMBANG_BAWAAN, match


def selesaikan_penamaan(con, crop_id, product_id, threshold=AMBANG_BAWAAN):
    """Kaitkan crop ke produk lalu betulkan hitungan scan yang bersangkutan.

    Pemanggil bertanggung jawab memastikan crop dan produknya ada, dan crop
    belum pernah di-resolve. Embedding crop ke galeri juga urusan pemanggil:
    `assign` memasukkannya, `produk-baru` sudah memakainya sebagai embedding
    utama produk.

    Return {"dipindah": int, "ikut_terbawa": [crop_id, ...]}.

    `dipindah` adalah total hitungan yang berpindah ke produk, termasuk yang
    datang dari crop hasil penyapuan. `ikut_terbawa` adalah crop lain yang ikut
    dikenali, supaya antarmuka dapat menghapus kartunya sekaligus alih-alih
    meninggalkannya di layar sebagai barang yang seolah masih misterius.

    Scan yang sudah diterapkan ke buku stok tidak disentuh hitungannya: laporan
    yang sudah dibukukan harus tetap sama dengan apa yang dulu dibukukan.
    Penamaannya sendiri tetap berlaku untuk scan berikutnya.
    """
    crop = db.get_unknown_crop(con, crop_id)
    scan_id = crop["scan_id"]
    db.resolve_unknown_crop(con, crop_id, product_id)

    scan = db.get_scan(con, scan_id)
    if scan is None or scan["terapkan_pada"] is not None:
        return {"dipindah": 0, "ikut_terbawa": []}

    dipindah = db.pindahkan_hitungan_unknown(con, scan_id, product_id, 1)

    # Galeri baru diambil SESUDAH resolve di atas, supaya embedding yang barusan
    # ditambahkan ikut jadi pembanding. Itu justru inti penyapuan ini: crop yang
    # tadi kalah tipis terhadap foto pendaftaran bisa menang telak terhadap crop
    # tetangganya yang diambil dari rak yang sama.
    products = db.all_products(con, with_gallery=True)
    ikut = []
    for lain in db.list_unknown_crops(con, scan_id=scan_id, hanya_belum=True):
        penuh = db.get_unknown_crop(con, lain["id"])
        if penuh is None:
            continue
        # Dicocokkan ke SELURUH produk, bukan hanya produk yang barusan dinamai.
        # Membatasi kandidat akan memaksa crop milik produk lain jatuh ke sini
        # hanya karena tidak ada pembanding lain.
        pid, _ = match(penuh["embedding"], products, threshold=threshold)
        if pid != product_id:
            continue
        db.resolve_unknown_crop(con, lain["id"], product_id)
        dipindah += db.pindahkan_hitungan_unknown(con, scan_id, product_id, 1)
        ikut.append(lain["id"])

    return {"dipindah": dipindah, "ikut_terbawa": ikut}
