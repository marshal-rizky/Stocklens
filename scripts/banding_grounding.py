"""Banding detektor sekarang (YOLO) vs detektor berbasis teks (Grounding DINO).

KENAPA SKRIP INI ADA
--------------------
PANDUAN-FINETUNE Step 1.5 mengukur bahwa detektor kita mewarisi prior SKU-110K:
produk hampir selalu kecil, tegak, berjejer. Akibatnya barang besar/pipih di
foto warung sering gagal — kadang pecah jadi serpihan, kadang hilang sama sekali.

Skrip ini menguji apakah detektor yang digerakkan FRASA TEKS punya batasan yang
sama. Grounding DINO menautkan frasa ke wilayah gambar, bukan mencocokkan pola
rak supermarket, jadi ia tidak membawa prior itu.

APA YANG DIUKUR, DAN APA YANG TIDAK
-----------------------------------
Sama seperti `baseline_detektor.py`: ini BUKAN mAP. Belum ada label manusia, dan
angka akurasi tanpa label adalah karangan. Yang direkam adalah perilaku yang
bisa diukur tanpa label — jumlah kotak dan luas kotak terbesar relatif frame —
karena persis di situ perbedaannya terlihat.

Kotak hasil skrip ini TETAP HARUS DIPERIKSA MANUSIA sebelum dipakai melatih.
Lihat ATURAN LABELING di Step 1.5.

CATATAN PROMPT
--------------
Grounding DINO memecah teks jadi frasa. Frasa "a packaged product on a shelf"
menghasilkan kotak terpisah berlabel "shelf" seluas 68 % frame — sampah. Pakai
frasa benda saja: "a packaged product." Frasa spesifik ("a bag of instant
noodles.") mempersempit hasil ke satu barang itu saja.

Pakai (dari akar repo; satu baris — `\` penyambung baris tidak jalan di cmd.exe):
    python -m scripts.banding_grounding --foto "<folder atau berkas>" --gambar "<folder keluaran>"
"""
import argparse
import glob
import json
import os

MODEL_GD = "IDEA-Research/grounding-dino-base"
CONF_PRODUKSI = 0.25   # ambang yang dipakai aplikasi
AMBANG_GD = 0.30
AMBANG_TEKS_GD = 0.25


def kumpulkan(target):
    if os.path.isfile(target):
        return [target]
    pola = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG")
    berkas = []
    for p in pola:
        berkas += glob.glob(os.path.join(target, "**", p), recursive=True)
    return sorted(set(berkas))


def persen_luas(kotak, wh):
    total = wh[0] * wh[1]
    return [max(0.0, (b[2] - b[0])) * max(0.0, (b[3] - b[1])) / total * 100
            for b in kotak]


def gambar_kotak(path, kotak, keluar, warna):
    from PIL import Image, ImageDraw
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    for b in kotak:
        d.rectangle(list(b), outline=warna, width=max(3, im.size[0] // 340))
    im.thumbnail((1400, 1400))
    im.save(keluar, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True, help="berkas atau folder foto")
    ap.add_argument("--frasa", default="a packaged product.",
                    help="frasa benda, huruf kecil, diakhiri titik")
    ap.add_argument("--bobot", default=os.environ.get("STOKLENS_MODEL", "yolo11n.pt"))
    ap.add_argument("--conf-yolo", type=float, default=CONF_PRODUKSI)
    ap.add_argument("--gambar", help="folder untuk menyimpan foto berkotak")
    ap.add_argument("--keluar", default="banding_grounding.json")
    a = ap.parse_args()

    berkas = kumpulkan(a.foto)
    if not berkas:
        raise SystemExit(f"tidak ada foto di {a.foto}")
    if a.gambar:
        os.makedirs(a.gambar, exist_ok=True)

    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
    from ultralytics import YOLO

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    yolo = YOLO(a.bobot)
    proc = AutoProcessor.from_pretrained(MODEL_GD)
    gdino = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_GD).to(dev)

    print(f"{len(berkas)} foto | bobot {a.bobot} | frasa {a.frasa!r} | {dev}\n")
    print(f"{'foto':44s} {'YOLO n':>7s} {'maks%':>7s} {'GD n':>6s} {'maks%':>7s}")

    baris = []
    for f in berkas:
        im = Image.open(f).convert("RGB")

        r = yolo.predict(f, conf=a.conf_yolo, imgsz=640, max_det=1000,
                         verbose=False)[0]
        ky = ([] if r.boxes is None
              else [[float(v) for v in b] for b in r.boxes.xyxy.cpu().numpy()])

        inp = proc(images=im, text=a.frasa, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = gdino(**inp)
        h = proc.post_process_grounded_object_detection(
            out, inp.input_ids, threshold=AMBANG_GD,
            text_threshold=AMBANG_TEKS_GD, target_sizes=[im.size[::-1]])[0]
        kg = [[float(v) for v in b] for b in h["boxes"].cpu().numpy()]
        sg = [float(s) for s in h["scores"].cpu().numpy()]

        ly, lg = persen_luas(ky, im.size), persen_luas(kg, im.size)
        nama = os.path.relpath(f, a.foto if os.path.isdir(a.foto) else os.path.dirname(f))
        baris.append({
            "foto": nama,
            "yolo": {"kotak": len(ky), "maks_persen": round(max(ly, default=0), 2)},
            "gdino": {"kotak": len(kg), "maks_persen": round(max(lg, default=0), 2),
                      "conf_maks": round(max(sg, default=0), 3)},
        })
        print(f"{nama[-44:]:44s} {len(ky):7d} {max(ly, default=0):7.2f}"
              f" {len(kg):6d} {max(lg, default=0):7.2f}")

        if a.gambar:
            dasar = os.path.splitext(os.path.basename(f))[0][:40]
            gambar_kotak(f, ky, os.path.join(a.gambar, f"{dasar}-YOLO.jpg"), (255, 40, 40))
            gambar_kotak(f, kg, os.path.join(a.gambar, f"{dasar}-GDINO.jpg"), (40, 200, 60))

    hasil = {"bobot": a.bobot, "frasa": a.frasa, "conf_yolo": a.conf_yolo,
             "model_gdino": MODEL_GD, "baris": baris}
    with open(a.keluar, "w", encoding="utf-8") as fh:
        json.dump(hasil, fh, indent=1, ensure_ascii=False)

    ny = sum(1 for b in baris if b["yolo"]["kotak"] == 0)
    ng = sum(1 for b in baris if b["gdino"]["kotak"] == 0)
    print(f"\nfoto tanpa kotak — YOLO: {ny}/{len(baris)}, Grounding DINO: {ng}/{len(baris)}")
    print(f"-> {a.keluar}")
    print("\nCATATAN: ini BUKAN mAP. Kotak wajib diperiksa manusia sebelum dilatih.")


if __name__ == "__main__":
    main()
