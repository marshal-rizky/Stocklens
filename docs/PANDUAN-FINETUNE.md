# Panduan Fine-tuning Model StokLens

> Prasyarat: dataset YOLO format dari Roboflow (lihat `PANDUAN-DATASET.md`).
> PENTING (rulebook AIC): model WAJIB di-fine-tune. Dokumen ini + screenshot hasilnya
> = bukti compliance. Simpan semuanya.

## Di mana training dijalankan (cek 18 Jul 2026)

**Laptop ketua tim = pilihan terbaik. JANGAN beli Colab Pro.**

Laptop ketua punya **RTX 4070 12GB** — sekitar **2–3× lebih cepat dari T4** yang dipakai
Colab (gratis maupun Pro tier standar), tanpa batas waktu sesi dan tanpa risiko
disconnect di tengah training. VRAM 12GB lebih dari cukup untuk YOLO11n/s @640px.

✅ **SUDAH DIPERBAIKI (18 Jul 2026).** Sebelumnya PyTorch terpasang build **CPU-only**
(`2.13.0+cpu`) sehingga GPU tidak terpakai sama sekali. Sekarang `2.13.0+cu126`,
`torch.cuda.is_available() == True`, RTX 4070 terdeteksi.

Perintah yang dipakai (untuk anggota tim lain yang punya GPU NVIDIA):

```bash
pip install --index-url https://download.pytorch.org/whl/cu126 \
    "torch==2.13.0+cu126" "torchvision==0.28.0+cu126"
python -c "import torch; print(torch.cuda.is_available())"   # harus True
```

⚠️ **Pakai index `cu126`, JANGAN `cu124`.** Saat dicek, `cu124` hanya menyediakan
torch sampai 2.6.0 — memakainya akan MENURUNKAN torch dari 2.13.0 dan berisiko
merusak ultralytics 8.4.90 / open_clip 3.3.0. Selalu cek dulu:
`pip index versions torch --index-url https://download.pytorch.org/whl/<cuXXX>`
dan pilih index yang punya versi torch yang sama dengan yang sedang terpasang.

Hasil verifikasi setelah upgrade: seluruh test cepat + 2 test slow hijau, semua modul
(ultralytics, open_clip, easyocr, stoklens) import normal. **CLIP jadi ~3,3× lebih
cepat** (19 ms → 6 ms per gambar).

**Perbandingan opsi:**

| Opsi | GPU | Batas | Biaya |
|---|---|---|---|
| **RTX 4070 lokal** (disarankan) | Setara/di atas L4 | Tidak ada | Rp0 |
| Colab gratis | T4 (kalau kebagian) | Sering putus, sesi pendek | Rp0 |
| Colab Pro | T4/L4, background run | 24 jam | ~Rp170k/bln |
| Kaggle Notebooks | P100 / T4×2 | 30 jam GPU/minggu, sesi 12 jam | Rp0 |

Colab/Kaggle tetap berguna untuk anggota tim yang **tidak punya GPU**, atau kalau mau
training jalan sementara laptop dipakai kerja lain. Untuk itu **versi gratis sudah cukup**
— dan Kaggle lebih longgar dari Colab gratis. Perintah training di bawah sama saja,
tinggal jalankan di mana pun (di lokal, hapus baris `!pip install`).

## Gambaran alur

```
yolo11n.pt (COCO, generik)
   │  Step 1: pre-train di SKU-110K (11rb foto rak retail, publik)
   ▼
model "ngerti rak retail"
   │  Step 2: fine-tune di dataset gudang kita sendiri
   ▼
stoklens-yolo.pt  ← dipakai di aplikasi
```

Kenapa dua tahap: SKU-110K mengajari model bentuk umum "rak penuh produk rapat"
(dataset kita terlalu kecil untuk itu), dataset sendiri mengajari kondisi lokal
(kemasan Indonesia, pencahayaan warung, rak semi-rapi). Hasilnya lebih akurat
daripada langsung fine-tune dari COCO, dan cerita compliance-nya lebih kuat.

## Step 0 — Baseline (5 menit, JANGAN skip)

Ukur dulu model generik di test set kita, supaya punya angka "sebelum":

```python
!pip -q install ultralytics
from ultralytics import YOLO
model = YOLO("yolo11n.pt")
metrics = model.val(data="/content/dataset/data.yaml", split="test")
print("BASELINE mAP50:", metrics.box.map50)   # catat angka ini!
```

(`/content/dataset` = hasil unzip export Roboflow; `data.yaml` sudah dibuatkan Roboflow.)

## Step 1 — Pre-train di SKU-110K — ✅ SUDAH DIJALANKAN 2026-07-28

**Tidak perlu diulang.** Step ini tidak butuh dataset sendiri, jadi sengaja
dikerjakan lebih awal supaya GPU tidak menganggur menunggu foto rak terkumpul.
Hasilnya jadi titik awal Step 2.

### Hasil yang sudah didapat (RTX 4070, 20 epoch, 37 menit)

| Epoch | mAP50 | mAP50-95 |
|---|---|---|
| 1 | 0,756 | 0,408 |
| 11 | 0,850 | 0,505 |
| **20 (final)** | **0,868** | **0,525** |

Validasi akhir 588 gambar / 90.968 objek: precision **0,894**, recall **0,816**,
inferensi **1,7 ms** per gambar. Kurva sudah melandai — epoch 11→20 cuma naik
0,018 mAP50, jadi menambah epoch tidak sepadan.

Checkpoint: `pretrain_sku110k/weights/best.pt` (5,2 MB).

### Kalau tetap perlu menjalankan ulang

```python
# WAJIB dibungkus __main__ — lihat penjelasan di bawah
from ultralytics import YOLO


def main():
    model = YOLO("yolo11n.pt")
    model.train(data="SKU-110K.yaml", epochs=20, imgsz=640, batch=16,
                workers=4,
                project=r"C:\Users\<kamu>\StokLens-training",  # DI LUAR repo
                name="pretrain_sku110k")


if __name__ == "__main__":
    main()
```

**Dua jebakan yang sudah memakan korban — jangan salin perintah versi Colab
mentah-mentah ke Windows:**

1. **`project` harus DI LUAR repo.** Versi lama dokumen ini menulis
   `project="stoklens"`. Di Colab itu aman (`/content`), tapi di repo kita
   `stoklens/` adalah **nama package Python-nya** — hasil training akan
   menumpuk di dalam source code dan berisiko ikut ter-commit.

2. **Bungkus dalam `if __name__ == "__main__":`.** DataLoader PyTorch di
   Windows memakai `spawn`, yang meng-import ulang modul utama di tiap worker.
   Tanpa guard ini prosesnya beranak-pinak lalu mati dengan *"An attempt has
   been made to start a new process before the current process has finished
   its bootstrapping phase"* — dan matinya SETELAH mengunduh 11,4 GB. Di
   Linux/Colab tidak terjadi karena pakai `fork`.

**Catatan lapangan lain:**

- Unduhan `SKU110K_fixed.tar.gz` **11,4 GB**, hasil ekstraksi **13,6 GB**
  (23.495 file) ke `~/stoklens/datasets/`. Sediakan ±25 GB kosong.
- `batch=16` @ 640px memakan **11,7 dari 12 GB VRAM** — nyaris mentok. Jangan
  pakai GPU untuk hal lain selama training; turunkan ke `batch=8` kalau OOM.
- Peringatan `Corrupt JPEG data` akan muncul ratusan kali. **Normal** — SKU-110K
  memang punya JPEG cacat ringan, libjpeg memulihkannya sendiri.
- Kalau dijalankan di Colab gratis dan kena limit: `epochs=10` sudah lumayan
  untuk transfer learning.

## Step 2 — Fine-tune di dataset sendiri (±1–2 jam)

Berlaku dua jebakan yang sama seperti Step 1 — `project` di luar repo, dan
dibungkus `__main__`:

```python
from ultralytics import YOLO


def main():
    model = YOLO(r"C:\Users\<kamu>\StokLens-training\pretrain_sku110k\weights\best.pt")
    model.train(data="dataset/data.yaml", epochs=60, imgsz=640, batch=16,
                patience=15,      # early stop kalau 15 epoch tidak membaik
                workers=4,
                project=r"C:\Users\<kamu>\StokLens-training",
                name="finetune_gudang")


if __name__ == "__main__":
    main()
```

## Step 3 — Evaluasi & bukti (bahan pitch!)

```python
best = YOLO("stoklens/finetune_gudang/weights/best.pt")
m = best.val(data="/content/dataset/data.yaml", split="test")
print("SESUDAH mAP50:", m.box.map50)
```

Simpan untuk pitch deck:
1. Tabel: mAP50 baseline vs sesudah fine-tune.
2. `results.png` (kurva training) dari folder run.
3. 3–4 contoh gambar prediksi berdampingan (sebelum: bolong/salah; sesudah: rapi) —
   `best.predict("foto_test.jpg", save=True)`.
4. **Uji generalisasi**: prediksi di foto dari lokasi yang TIDAK ada di training.
   Kalau bagus → klaim kuat; kalau jelek → jujur, tambah data lokasi itu.

## Step 4 — Pasang di aplikasi

1. `best.pt` → rename `stoklens-yolo.pt` → taruh **Drive tim** (JANGAN commit — .gitignore memblokir `*.pt`).
2. Tiap orang download ke root repo lokal.
3. Pakai: `run_scan(..., model_path="stoklens-yolo.pt")` dan
   `scan_photos(..., detector=None)` otomatis lewat `_yolo_detector("stoklens-yolo.pt")`
   — atau set default `model_path` di `scan.py`/`photo.py` lewat PR.

## Jebakan umum

| Gejala | Penyebab | Obat |
|---|---|---|
| mAP training tinggi, test jelek | Overfit / data seragam | Tambah variasi foto, kecilkan epoch, cek augmentasi |
| Bagus di toko A, jelek di toko B | Generalisasi kurang | Tambah data toko B (50–100 foto sering cukup) |
| Deteksi dobel bertumpuk | NMS | `best.predict(..., iou=0.5)` — turunkan iou |
| Kotak kegedean/longgar | Labeling tidak konsisten | QC ulang label (aturan di PANDUAN-DATASET) |
| Colab disconnect | Sesi gratis terbatas | Checkpoint ke Drive tiap run; `resume=True` |

## (Opsional) Fine-tune CLIP — metric learning

**Kapan perlu:** kalau uji lapangan menunjukkan banyak salah-match antar varian mirip
(Indomie goreng vs soto) DAN guided mode dirasa merepotkan user.

**Kalau tidak sempat: boleh skip.** Justifikasi tertulis untuk juri: "CLIP zero-shot +
guided mode + majority voting sudah mencapai akurasi X% di uji lapangan; fine-tune CLIP
masuk roadmap." Syarat wajib fine-tune rulebook sudah terpenuhi oleh YOLO.

Garis besar kalau dikerjakan:
1. Dataset: crop hasil deteksi, dikelompokkan per SKU (±30–50 crop/SKU, ambil dari
   foto dataset + enrollment). 
2. Training: contrastive/triplet — crop SKU sama = positif, beda = negatif. Fine-tune
   hanya beberapa layer terakhir image encoder (`open_clip`), 10–20 epoch, LR kecil (1e-5).
3. Evaluasi: akurasi top-1 matching di crop test vs CLIP vanilla — pakai galeri
   enrollment sungguhan.
4. Hasil `.pt` → Drive; ganti `model_name/pretrained` di `ClipEmbedder`.

## Checklist compliance rulebook

- [ ] Angka baseline tercatat (Step 0) — **menunggu dataset sendiri**
- [x] Step 1 pre-train SKU-110K selesai + angkanya tercatat (28 Jul, mAP50 0,868)
- [ ] Kurva training + config tersimpan (Step 1 & 2)
- [ ] Tabel sebelum/sesudah + contoh prediksi (Step 3)
- [ ] Model custom terpasang & dipakai demo (Step 4)
- [ ] Satu slide pitch khusus "Fine-tuning kami": dua tahap + angka
