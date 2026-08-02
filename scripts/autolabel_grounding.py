"""Hasilkan anotasi awal format YOLO memakai detektor berbasis teks (Grounding DINO).

Ini pengganti blok `model.predict(save_txt=True, conf=0.05)` di PANDUAN-DATASET
Tahap 3. Sisa alurnya tidak berubah: hasilnya di-upload ke Roboflow sebagai
anotasi awal, tim mengoreksi, lalu Generate.

KENAPA BUKAN MODEL KITA SENDIRI
-------------------------------
Model pre-train kita mewarisi prior SKU-110K (produk kecil, tegak, berjejer).
Diukur 2 Agustus di 12 foto demo, kotak terbesarnya tidak pernah lewat ~14 %
frame, dan pada tiga foto dekat satu barang ia memberi NOL kotak. Grounding DINO
menautkan frasa teks ke wilayah gambar, tidak membawa prior itu, dan pada foto
yang sama menghasilkan kotak 25–62 % yang benar. Rinciannya di PANDUAN-FINETUNE
Step 1.6.

SATU KELAS SAJA
---------------
Dataset ini satu kelas: `produk`. Grounding DINO tidak perlu tahu nama barang —
identitas produk datang dari pencocokan CLIP saat enroll, bukan dari detektor.

KOTAKNYA WAJIB DIPERIKSA MANUSIA
--------------------------------
Skrip ini TIDAK menghasilkan label siap latih. Dua kelemahan sudah terukur:
pada foto warung padat banyak barang latar terlewat, dan kadang muncul satu
kotak raksasa yang menelan satu rak. Keduanya harus dibereskan di Roboflow.
Barang yang tidak terkotak lalu ikut dilatih akan mengajari model bahwa barang
itu latar — bahaya yang sama dengan aturan "gabung serpihan".

Pakai (dari akar repo; satu baris — `\` penyambung baris tidak jalan di cmd.exe):
    pip install "transformers>=4.44"

    python -m scripts.autolabel_grounding --foto "<folder foto>" --keluar "<folder hasil>"
"""
import argparse
import glob
import os
import shutil

MODEL_GD = "IDEA-Research/grounding-dino-base"
FRASA = "a packaged product."
AMBANG = 0.25        # lihat tabel di PANDUAN-FINETUNE Step 1.6
AMBANG_TEKS = 0.20
IOU_NMS = 0.5
EKSTENSI = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")


def kumpulkan(target, abaikan=()):
    """Kumpulkan foto, lewati folder yang diabaikan.

    `abaikan` selalu memuat folder keluaran. Tanpa itu, menaruh --keluar di dalam
    --foto membuat jalan kedua memakan keluarannya sendiri: gambar hasil rotasi
    ikut terbaca sebagai foto mentah, lalu dilabeli lagi.
    """
    if os.path.isfile(target):
        return [target]
    tolak = [os.path.normcase(os.path.abspath(a)) + os.sep for a in abaikan]
    berkas = []
    for p in EKSTENSI:
        berkas += glob.glob(os.path.join(target, "**", p), recursive=True)
    return sorted({f for f in berkas
                   if not any(os.path.normcase(os.path.abspath(f)).startswith(t)
                              for t in tolak)})


def nama_unik(path, akar, dipakai):
    """Nama datar & unik. Foto bisa bersarang dan bernama sama di folder berbeda;
    kalau ditumpuk begitu saja, label satu foto menimpa label foto lain."""
    rel = os.path.relpath(path, akar) if os.path.isdir(akar) else os.path.basename(path)
    dasar = os.path.splitext(rel)[0].replace(os.sep, "__").replace(" ", "-")
    kandidat, n = dasar, 2
    while kandidat in dipakai:
        kandidat, n = f"{dasar}-{n}", n + 1
    dipakai.add(kandidat)
    return kandidat


def ke_yolo(kotak, lebar, tinggi):
    """xyxy piksel -> '0 xc yc w h' ternormalisasi, dijepit ke dalam frame."""
    baris = []
    for x1, y1, x2, y2 in kotak:
        x1, y1 = max(0.0, x1), max(0.0, y1)
        x2, y2 = min(float(lebar), x2), min(float(tinggi), y2)
        w, h = x2 - x1, y2 - y1
        if w <= 1 or h <= 1:
            continue
        baris.append(f"0 {((x1 + x2) / 2) / lebar:.6f} {((y1 + y2) / 2) / tinggi:.6f}"
                     f" {w / lebar:.6f} {h / tinggi:.6f}")
    return baris


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True, help="berkas atau folder foto mentah")
    ap.add_argument("--keluar", required=True, help="folder hasil")
    ap.add_argument("--frasa", default=FRASA,
                    help="frasa BENDA saja, huruf kecil, diakhiri titik")
    ap.add_argument("--ambang", type=float, default=AMBANG)
    ap.add_argument("--ambang-teks", type=float, default=AMBANG_TEKS)
    ap.add_argument("--abaikan", nargs="*", default=[],
                    help="folder yang dilewati (folder --keluar otomatis dilewati)")
    a = ap.parse_args()

    berkas = kumpulkan(a.foto, [a.keluar, *a.abaikan])
    if not berkas:
        raise SystemExit(f"tidak ada foto di {a.foto}")

    d_img = os.path.join(a.keluar, "images")
    d_lbl = os.path.join(a.keluar, "labels")
    os.makedirs(d_img, exist_ok=True)
    os.makedirs(d_lbl, exist_ok=True)

    import torch
    from PIL import Image, ImageOps
    from torchvision.ops import nms
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(MODEL_GD)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_GD).to(dev)

    print(f"{len(berkas)} foto | frasa {a.frasa!r} | ambang {a.ambang} | {dev}")
    print(f"-> {a.keluar}\n")

    dipakai, total, kosong = set(), 0, []
    for i, f in enumerate(berkas, 1):
        try:
            im = Image.open(f)
            # Terapkan rotasi EXIF SEBELUM deteksi, lalu simpan gambar yang sudah
            # dirotasi. Kalau tidak, kotak dihitung pada orientasi berbeda dari
            # yang ditampilkan Roboflow dan seluruh label meleset.
            im = ImageOps.exif_transpose(im).convert("RGB")
        except Exception as e:                     # foto rusak jangan menghentikan batch
            print(f"  [{i}/{len(berkas)}] LEWAT (tidak terbaca): {f} — {e}")
            continue
        W, H = im.size

        inp = proc(images=im, text=a.frasa, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = model(**inp)
        h = proc.post_process_grounded_object_detection(
            out, inp.input_ids, threshold=a.ambang,
            text_threshold=a.ambang_teks, target_sizes=[(H, W)])[0]

        bs, sc = h["boxes"], h["scores"]
        if len(bs):
            bs = bs[nms(bs, sc, IOU_NMS)]
        baris = ke_yolo([[float(v) for v in b] for b in bs.cpu().numpy()], W, H)

        nama = nama_unik(f, a.foto, dipakai)
        im.save(os.path.join(d_img, f"{nama}.jpg"), quality=92)
        with open(os.path.join(d_lbl, f"{nama}.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(baris) + ("\n" if baris else ""))

        total += len(baris)
        if not baris:
            kosong.append(nama)
        if i % 10 == 0 or i == len(berkas):
            print(f"  [{i}/{len(berkas)}] {total} kotak sejauh ini")

    with open(os.path.join(a.keluar, "data.yaml"), "w", encoding="utf-8") as fh:
        fh.write(
            "# JANGAN melatih langsung dari berkas ini.\n"
            "# train dan val menunjuk folder yang SAMA — model akan diuji memakai\n"
            "# foto yang dilatihkan, jadi nilainya pasti bagus dan pasti bohong.\n"
            "# Berkas ini cuma penanda untuk impor Roboflow; pembagian 80/10/10\n"
            "# yang sebenarnya dibuat Roboflow di tahap Generate.\n"
            "path: .\ntrain: images\nval: images\nnc: 1\nnames: ['produk']\n")

    n = len(dipakai)
    print(f"\n{n} foto, {total} kotak (rata-rata {total / max(1, n):.1f} per foto)")
    if kosong:
        print(f"{len(kosong)} foto TANPA kotak — wajib digambar manual di Roboflow:")
        for k in kosong[:10]:
            print(f"  - {k}")
        if len(kosong) > 10:
            print(f"  ... dan {len(kosong) - 10} lagi")
    print("\nUpload folder images/ + labels/ ke Roboflow sebagai anotasi awal.")
    print("INI BELUM SIAP LATIH. Tim wajib menambah kotak yang terlewat dan")
    print("membuang kotak raksasa yang menelan satu rak — lihat PANDUAN-DATASET.")


if __name__ == "__main__":
    main()
