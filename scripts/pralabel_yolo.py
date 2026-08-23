"""Pra-label foto baru memakai detektor StokLens sendiri, lalu bagi per anotator.

KENAPA MODEL SENDIRI, BUKAN GROUNDING DINO LAGI
-----------------------------------------------
Gelombang pertama dilabeli Grounding DINO karena waktu itu belum ada detektor
yang tahu apa-apa soal rak warung. Sekarang ada, dan pada toko yang ditahan
penuh dari data latih ia mencapai mAP50 0,846. Memakainya untuk pra-label
mengubah pekerjaan anotator dari menggambar ratusan kotak jadi mengoreksi
kotak yang sudah ada, dan pada tumpukan rokok bedanya berjam-jam.

BAHAYA YANG DIBAYAR DENGAN SETELAN
----------------------------------
Melabeli data dengan model yang justru mau diperbaiki punya satu jebakan:
anotator memperbaiki kotak yang salah, tetapi hampir tidak pernah menyadari
kotak yang TIDAK ADA. Barang yang model lewatkan akan tetap terlewat di label,
lalu model berikutnya belajar bahwa benda itu memang bukan objek, dan mAP tidak
akan memperlihatkannya karena label dan model sepakat pada kesalahan yang sama.

Karena itu `conf` bawaannya 0,10, jauh di bawah nilai yang wajar untuk
produksi. Model sengaja disuruh kebanyakan menebak. Menghapus kotak berlebih
itu satu klik; menyadari kotak yang hilang butuh menyisir foto. Selalu pilih
beban kerja yang pertama.

`max_det` dinaikkan ke 1000 karena bawaan ultralytics 300 diam-diam memotong
hasil, dan satu foto rak rokok bisa memuat lebih dari itu.

HEIC DAN ORIENTASI EXIF
-----------------------
Foto iPhone datang sebagai HEIC dan menyimpan orientasi di EXIF, bukan pada
piksel. OpenCV mengabaikan tanda itu, jadi foto potret masuk ke model dalam
posisi rebah; pada gelombang pertama satu foto menghasilkan nol kotak karena
ini. Gambar diputar lebih dulu, lalu yang DISIMPAN adalah versi yang sudah
diputar, supaya kotak dan gambar yang dilihat anotator selalu cocok.

Ubin sengaja TIDAK dipakai. Ubin memperbesar objek relatif terhadap masukan
model, dan diukur pada 22 Agustus resolusi inferensi yang lebih besar justru
menurunkan recall (0,781 di 640 jadi 0,711 di 1600) karena model dilatih pada
skala tertentu. Kalau nanti ubin mau dipakai, ukur dulu.

    python scripts/pralabel_yolo.py datasets/gelombang-3/mentah \
        --keluar datasets/gelombang-3/siap --bagian 4
"""

import argparse
import pathlib
import shutil

import numpy as np
import pillow_heif
from PIL import Image, ImageOps

BOBOT_BAWAAN = r"C:\Users\User\StokLens-training\finetune_1280\weights\best.pt"
SISI_MAKS = 2048

pillow_heif.register_heif_opener()


def muat_tegak(path):
    """Baca foto apa pun (termasuk HEIC), tegakkan sesuai EXIF, batasi sisinya."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if max(img.size) > SISI_MAKS:
        skala = SISI_MAKS / max(img.size)
        img = img.resize((round(img.width * skala), round(img.height * skala)),
                         Image.LANCZOS)
    return img


def tulis_label(path_txt, kotak, lebar, tinggi):
    """Tulis satu file label YOLO. Satu kelas saja, jadi indeksnya selalu 0."""
    baris = []
    for x1, y1, x2, y2 in kotak:
        # Dijepit ke dalam bingkai: kotak yang keluar batas ditolak diam-diam
        # oleh Roboflow, dan pada gelombang pertama 208 kotak hilang begitu.
        x1, y1 = max(x1, 0.0), max(y1, 0.0)
        x2, y2 = min(x2, float(lebar)), min(y2, float(tinggi))
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        baris.append("0 %.6f %.6f %.6f %.6f" % (
            ((x1 + x2) / 2) / lebar, ((y1 + y2) / 2) / tinggi,
            (x2 - x1) / lebar, (y2 - y1) / tinggi))
    path_txt.write_text("\n".join(baris) + ("\n" if baris else ""), encoding="utf-8")
    return len(baris)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sumber", help="folder foto mentah")
    p.add_argument("--keluar", required=True, help="folder hasil")
    p.add_argument("--bobot", default=BOBOT_BAWAAN)
    p.add_argument("--conf", type=float, default=0.10)
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--bagian", type=int, default=1, help="jumlah folder anotator")
    args = p.parse_args()

    from ultralytics import YOLO

    sumber = pathlib.Path(args.sumber)
    keluar = pathlib.Path(args.keluar)
    if keluar.exists():
        shutil.rmtree(keluar)
    keluar.mkdir(parents=True)

    fotos = sorted(f for f in sumber.iterdir()
                   if f.suffix.lower() in (".heic", ".jpg", ".jpeg", ".png"))
    if not fotos:
        raise SystemExit(f"Tidak ada foto di {sumber}")

    model = YOLO(args.bobot)
    print(f"{len(fotos)} foto, bobot {pathlib.Path(args.bobot).parent.parent.name},"
          f" conf {args.conf}, imgsz {args.imgsz}", flush=True)

    # Bagi rata lebih dulu supaya tiap anotator dapat foto dari seluruh rentang
    # nomor urut, bukan satu blok berurutan. Foto berurutan biasanya satu rak
    # yang sama; membaginya per blok membuat satu orang mengerjakan satu jenis
    # rak saja, dan kesalahan penafsirannya jadi terkonsentrasi di situ.
    folder = []
    for i in range(args.bagian):
        d = keluar / f"bagian-{i + 1}" if args.bagian > 1 else keluar
        (d / "images").mkdir(parents=True, exist_ok=True)
        (d / "labels").mkdir(parents=True, exist_ok=True)
        folder.append(d)

    jumlah_kotak = []
    kosong = []
    for i, f in enumerate(fotos):
        img = muat_tegak(f)
        r = model.predict(np.array(img)[:, :, ::-1], imgsz=args.imgsz,
                          conf=args.conf, max_det=1000, verbose=False)[0]
        kotak = ([] if r.boxes is None
                 else [tuple(map(float, b)) for b in r.boxes.xyxy.cpu().numpy()])

        d = folder[i % args.bagian]
        nama = f.stem
        img.save(d / "images" / f"{nama}.jpg", "JPEG", quality=90)
        n = tulis_label(d / "labels" / f"{nama}.txt", kotak, img.width, img.height)
        jumlah_kotak.append(n)
        if n == 0:
            kosong.append(nama)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(fotos)}", flush=True)

    arr = np.array(jumlah_kotak)
    print(f"\nselesai. total kotak {int(arr.sum())}, rata-rata {arr.mean():.1f} per foto")
    print(f"  sebaran: min {arr.min()}, p25 {np.percentile(arr, 25):.0f},"
          f" median {np.median(arr):.0f}, p75 {np.percentile(arr, 75):.0f},"
          f" maks {arr.max()}")
    print(f"  foto tanpa kotak sama sekali: {len(kosong)}")
    if kosong:
        print("   ", ", ".join(kosong[:10]) + (" ..." if len(kosong) > 10 else ""))
    for d in folder:
        n = len(list((d / "images").glob("*.jpg")))
        print(f"  {d}  {n} foto")


if __name__ == "__main__":
    main()
