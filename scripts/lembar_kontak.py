"""Lembar kontak foto + kotaknya, untuk triase mata manusia sebelum unggah.

KENAPA MANUSIA, BUKAN PENYARING OTOMATIS
----------------------------------------
Pemilahan isi pakai CLIP zero-shot dicoba lebih dulu (2 Agustus) dan GAGAL.
Seluruh skor berdesak di 0,246-0,393 dan satu foto pemandangan jalan yang sudah
diverifikasi mata mendapat skor tepat di median. Tidak ada margin untuk
memutuskan apa pun. Masuk akal: foto itu memang memuat dinding warung penuh
kerupuk gantung, jadi prompt "rak penuh produk" cocok sebagian — CLIP menilai
gambar utuh, sedangkan masalahnya ada di komposisi.

Manusia mengenali "ini bukan rak" dalam sepersekian detik. Jadi yang dibuat di
sini bukan penyaring, melainkan alat supaya penilaian itu bisa dilakukan atas
ratusan foto dalam beberapa menit.

Yang MASIH otomatis adalah tanda merah: pola kotak-raksasa (sedikit kotak tapi
ada yang menelan >25% frame). Itu berbasis struktur, bukan tebakan makna, dan
cocok dengan mode gagal yang teramati di etalase rokok padat.

Pakai (dari akar repo; satu baris):
    python -m scripts.lembar_kontak --sumber "<folder hasil autolabel>"
"""
import argparse
import glob
import json
import os

KOLOM, BARIS, SEL, PAD = 6, 4, 340, 26
AMBANG_RAKSASA = 25.0   # % frame
MAKS_KOTAK_RAKSASA = 6  # kotak sedikit + salah satunya raksasa = mencurigakan


def baca_kotak(jalur_label):
    return [ln.split() for ln in open(jalur_label, encoding="utf-8") if ln.strip()]


def luas_persen(kotak):
    return [float(w) * float(h) * 100 for _, _, _, w, h in kotak]


def curiga(kotak):
    """Tanda kotak-raksasa: sedikit kotak, salah satunya menelan sebagian rak."""
    lu = luas_persen(kotak)
    if not lu:
        return "tanpa-kotak"
    if len(kotak) <= MAKS_KOTAK_RAKSASA and max(lu) > AMBANG_RAKSASA:
        return f"kotak-raksasa({len(kotak)} kotak, maks {max(lu):.0f}%)"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", required=True, help="folder keluaran autolabel_grounding")
    ap.add_argument("--keluar", help="default: <sumber>/_lembar-kontak")
    a = ap.parse_args()

    from PIL import Image, ImageDraw

    out = a.keluar or os.path.join(a.sumber, "_lembar-kontak")
    os.makedirs(out, exist_ok=True)
    gambar = sorted(glob.glob(os.path.join(a.sumber, "images", "*.jpg")))
    if not gambar:
        raise SystemExit(f"tidak ada foto di {a.sumber}/images")

    indeks, ditandai, per_lembar = [], [], KOLOM * BARIS
    for lembar in range((len(gambar) + per_lembar - 1) // per_lembar):
        kanvas = Image.new("RGB", (KOLOM * SEL, BARIS * (SEL + PAD)), (250, 248, 244))
        d = ImageDraw.Draw(kanvas)
        for k, g in enumerate(gambar[lembar * per_lembar:(lembar + 1) * per_lembar]):
            no = lembar * per_lembar + k + 1
            nama = os.path.basename(g)
            kotak = baca_kotak(os.path.join(a.sumber, "labels", nama[:-4] + ".txt"))
            tanda = curiga(kotak)

            im = Image.open(g).convert("RGB")
            W, H = im.size
            dd = ImageDraw.Draw(im)
            for _, xc, yc, w, h in kotak:
                xc, yc, w, h = map(float, (xc, yc, w, h))
                dd.rectangle([(xc - w / 2) * W, (yc - h / 2) * H,
                              (xc + w / 2) * W, (yc + h / 2) * H],
                             outline=(40, 220, 60), width=max(4, W // 220))
            im.thumbnail((SEL - 8, SEL - 8))
            kanvas.paste(im, ((k % KOLOM) * SEL + (SEL - im.size[0]) // 2,
                              (k // KOLOM) * (SEL + PAD) + PAD))
            d.text(((k % KOLOM) * SEL + 8, (k // KOLOM) * (SEL + PAD) + 6),
                   f"{no}. {len(kotak)} kotak{' !' if tanda else ''}",
                   fill=(200, 60, 40) if tanda else (40, 40, 40))
            indeks.append({"no": no, "nama": nama, "kotak": len(kotak), "tanda": tanda})
            if tanda:
                ditandai.append(nama)
        kanvas.save(os.path.join(out, f"lembar-{lembar + 1:02d}.jpg"), quality=84)

    json.dump(indeks, open(os.path.join(out, "indeks.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    with open(os.path.join(out, "ditandai.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ditandai) + ("\n" if ditandai else ""))

    n = (len(gambar) + per_lembar - 1) // per_lembar
    print(f"{len(gambar)} foto -> {n} lembar di {out}")
    print(f"{len(ditandai)} ditandai merah (pola kotak-raksasa / tanpa kotak)")
    print("\nBuka lembar-*.jpg, catat nomor yang ditolak. Sepuluh menit di sini")
    print("lebih murah daripada tim melabeli foto yang tidak layak.")


if __name__ == "__main__":
    main()
