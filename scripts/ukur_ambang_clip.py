"""Ukur ambang pencocokan CLIP dari foto enrollment — tanpa perlu labeling.

KENAPA INI ADA
--------------
Ambang 0,75 di `matcher.match()` belum pernah divalidasi. Angka yang ada cuma
kasus tunggal (0,769 / 0,823 / 0,664) — itu anekdot, bukan pengukuran. Padahal
pencocokan adalah separuh produk: detektor menjawab "ada barang di mana",
pencocokan menjawab "barang apa". Salah di sini membuat laporan opname menyebut
barang yang keliru, dan itu lebih buruk daripada tidak terdeteksi.

Foto enrollment sudah terkelompok per produk lewat nama folder Drive, jadi
kebenarannya sudah ada tanpa satu pun kotak digambar.

CARA UKUR — leave-one-out
-------------------------
Tiap foto sekali jadi foto uji; galeri produknya berisi SEMUA foto lain dari
produk itu, dan produk lain memakai galeri penuhnya. Jadi tiap foto diuji
melawan galeri yang tidak pernah memuat dirinya sendiri. Tanpa itu skornya
mendekati 1,0 dan pengukurannya jadi omong kosong — kesalahan yang sudah dua
kali terjadi di proyek ini (lihat docs/HASIL-UJI-2026-08-02.md).

Yang dipakai adalah `matcher.match()` ASLI dari repo, bukan tiruan, supaya yang
diukur memang perilaku produksi termasuk aturan max-similarity (bukan rata-rata).

BATAS YANG HARUS DIBACA
-----------------------
Foto enrollment adalah close-up satu barang; di produksi yang di-embed adalah
CROP hasil detektor dari foto rak. Jadi ini mengukur daya pisah matcher pada
data enrollment, BUKAN jalur produksi utuh. Angkanya batas atas yang optimistis
— crop dari rak lebih berantakan. Perlakukan sebagai "kalau di sini saja sudah
buruk, di produksi pasti lebih buruk".

Pakai (dari akar repo; satu baris):
    python -m scripts.ukur_ambang_clip --triase "<triase.json>" --triase-baru "<triase_baru.json>" --foto "<folder foto>"
"""
import argparse
import collections
import json
import os

# Folder tumpahan, bukan satu produk — memasukkannya membuat "kebenaran" palsu
# karena isinya campur banyak barang.
FOLDER_BUKAN_PRODUK = {"Data di Buah total", "Salinan Data Di Warung"}
MIN_FOTO = 3            # galeri >=2 + uji >=1
BUCKET = "2-ENROLLMENT-per-produk"
AMBANG_SAPU = [0.50, 0.55, 0.60, 0.65, 0.70, 0.72, 0.75, 0.78, 0.80, 0.85, 0.90]
AMBANG_PRODUKSI = 0.75


def produk_dari_path(x):
    bagian = x["path"].strip("/").split("/")
    return bagian[-2] if len(bagian) >= 2 else "?"


def kumpulkan(triase, triase_baru, folder_foto):
    from scripts.testset import muat_triase
    semua = muat_triase(triase, triase_baru)
    per = collections.defaultdict(list)
    for x in semua:
        if x["bucket"] != BUCKET:
            continue
        nama_produk = produk_dari_path(x)
        if nama_produk in FOLDER_BUKAN_PRODUK:
            continue
        jalur = os.path.join(folder_foto, f"{x['id']}__{x['nama']}")
        if os.path.exists(jalur):
            per[nama_produk].append(jalur)
    return {k: sorted(v) for k, v in per.items() if len(v) >= MIN_FOTO}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triase", required=True)
    ap.add_argument("--triase-baru")
    ap.add_argument("--foto", required=True)
    ap.add_argument("--keluar", default="ambang_clip.json")
    a = ap.parse_args()

    per_produk = kumpulkan(a.triase, a.triase_baru, a.foto)
    if not per_produk:
        raise SystemExit("tidak ada produk dengan foto cukup")

    n_foto = sum(len(v) for v in per_produk.values())
    print(f"{len(per_produk)} produk, {n_foto} foto\n")
    for k, v in sorted(per_produk.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(v):3d}  {k[:56]}")

    from PIL import Image, ImageOps

    from stoklens.embedder import ClipEmbedder
    from stoklens.matcher import match

    emb = ClipEmbedder()
    print(f"\nCLIP di {emb.device}, meng-embed {n_foto} foto...")
    vek = {}
    for i, (nama, jalur) in enumerate(
            ((n, j) for n, js in per_produk.items() for j in js), 1):
        im = ImageOps.exif_transpose(Image.open(jalur)).convert("RGB")
        vek[jalur] = emb.embed_pil(im)
        if i % 20 == 0:
            print(f"  {i}/{n_foto}")

    ids = {nama: i for i, nama in enumerate(sorted(per_produk))}
    nama_dari_id = {i: n for n, i in ids.items()}

    # Leave-one-out: galeri produk asal TIDAK memuat foto yang sedang diuji.
    hasil = []
    for nama, jalur_list in per_produk.items():
        for uji in jalur_list:
            produk = []
            for n2, js2 in per_produk.items():
                galeri = [vek[j] for j in js2 if j != uji]
                if galeri:
                    produk.append({"id": ids[n2], "embeddings": galeri})
            # threshold=0 supaya dapat skor mentah; ambangnya disapu belakangan.
            pid, skor = match(vek[uji], produk, threshold=0.0)
            hasil.append({"produk_benar": nama, "produk_tebak": nama_dari_id[pid],
                          "skor": round(float(skor), 4), "foto": os.path.basename(uji)})

    print(f"\n{'ambang':>7} {'benar':>6} {'SALAH':>6} {'ditolak':>8} {'presisi':>8} {'recall':>7}")
    print("-" * 48)
    tabel = []
    for t in AMBANG_SAPU:
        benar = sum(1 for h in hasil if h["skor"] >= t and h["produk_tebak"] == h["produk_benar"])
        salah = sum(1 for h in hasil if h["skor"] >= t and h["produk_tebak"] != h["produk_benar"])
        tolak = len(hasil) - benar - salah
        presisi = benar / (benar + salah) if (benar + salah) else 0.0
        recall = benar / len(hasil)
        tabel.append({"ambang": t, "benar": benar, "salah": salah, "ditolak": tolak,
                      "presisi": round(presisi, 4), "recall": round(recall, 4)})
        tanda = "  <- dipakai sekarang" if t == AMBANG_PRODUKSI else ""
        print(f"{t:7.2f} {benar:6d} {salah:6d} {tolak:8d} {presisi:8.3f} {recall:7.3f}{tanda}")

    # ---- Bagian kedua: menolak produk yang TIDAK terdaftar ----
    # Bagian pertama hanya menguji pemilihan di antara produk yang sudah ada di
    # galeri. Padahal tugas utama ambang justru menolak barang asing: rak warung
    # penuh barang yang belum di-enroll, dan menyebutnya sebagai produk lain
    # adalah kesalahan paling merusak di laporan opname.
    #
    # Diuji dengan leave-one-PRODUCT-out: satu produk dibuang dari seluruh
    # galeri, lalu fotonya HARUS ditolak.
    asing = []
    for nama_keluar, jalur_list in per_produk.items():
        produk = [{"id": ids[n2], "embeddings": [vek[j] for j in js2]}
                  for n2, js2 in per_produk.items() if n2 != nama_keluar]
        for uji in jalur_list:
            pid, skor = match(vek[uji], produk, threshold=0.0)
            asing.append({"produk_asli": nama_keluar, "disangka": nama_dari_id[pid],
                          "skor": round(float(skor), 4)})

    print(f"\n=== Menolak produk ASING (leave-one-product-out, {len(asing)} foto) ===")
    print(f"{'ambang':>7} {'ditolak benar':>14} {'LOLOS (salah)':>14} {'akurasi tolak':>14}")
    print("-" * 54)
    for t in AMBANG_SAPU:
        tolak = sum(1 for h in asing if h["skor"] < t)
        lolos = len(asing) - tolak
        tanda = "  <- dipakai sekarang" if t == AMBANG_PRODUKSI else ""
        print(f"{t:7.2f} {tolak:14d} {lolos:14d} {tolak / len(asing):14.3f}{tanda}")
        for row in tabel:
            if row["ambang"] == t:
                row["asing_ditolak"] = tolak
                row["asing_lolos"] = lolos

    salah_semua = [h for h in hasil if h["produk_tebak"] != h["produk_benar"]]
    print(f"\nSalah tebak (apa pun ambangnya): {len(salah_semua)} dari {len(hasil)}")
    for h in sorted(salah_semua, key=lambda x: -x["skor"])[:12]:
        print(f"  {h['skor']:.3f}  {h['produk_benar'][:30]:32s} -> {h['produk_tebak'][:30]}")

    json.dump({"produk": {k: len(v) for k, v in per_produk.items()},
               "tabel": tabel, "hasil": hasil, "asing": asing},
              open(a.keluar, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"\n-> {a.keluar}")
    print("\nCATATAN: foto enrollment adalah close-up; produksi meng-embed crop")
    print("dari foto rak yang lebih berantakan. Angka ini batas ATAS.")


if __name__ == "__main__":
    main()
