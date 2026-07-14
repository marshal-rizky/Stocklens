# Panduan Fine-tuning Model StokLens

> Prasyarat: dataset YOLO format dari Roboflow (lihat `PANDUAN-DATASET.md`).
> Semua jalan di **Google Colab gratis (GPU T4)** — Runtime → Change runtime type → T4 GPU.
> PENTING (rulebook AIC): model WAJIB di-fine-tune. Dokumen ini + screenshot hasilnya
> = bukti compliance. Simpan semuanya.

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

## Step 1 — Pre-train di SKU-110K (±3–6 jam, sekali saja)

```python
from ultralytics import YOLO
model = YOLO("yolo11n.pt")
# ultralytics auto-download SKU-110K (±13 GB) — pastikan Colab storage cukup
model.train(data="SKU-110K.yaml", epochs=20, imgsz=640, batch=16,
            project="stoklens", name="pretrain_sku110k")
```

- Kalau kena limit Colab: kecilkan `epochs=10` — untuk transfer learning sudah lumayan.
- Simpan `stoklens/pretrain_sku110k/weights/best.pt` ke Drive. Ini checkpoint antara.

## Step 2 — Fine-tune di dataset sendiri (±1–2 jam)

```python
from ultralytics import YOLO
model = YOLO("/content/drive/MyDrive/stoklens/pretrain_sku110k_best.pt")
model.train(data="/content/dataset/data.yaml", epochs=60, imgsz=640, batch=16,
            patience=15,          # early stop kalau 15 epoch tidak membaik
            project="stoklens", name="finetune_gudang")
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

- [ ] Angka baseline tercatat (Step 0)
- [ ] Kurva training + config tersimpan (Step 1 & 2)
- [ ] Tabel sebelum/sesudah + contoh prediksi (Step 3)
- [ ] Model custom terpasang & dipakai demo (Step 4)
- [ ] Satu slide pitch khusus "Fine-tuning kami": dua tahap + angka
