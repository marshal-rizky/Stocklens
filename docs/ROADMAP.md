# Roadmap StokLens — Juli s/d September 2026

> Disepakati 2026-07-14. Deadline submission penyisihan: ±September 2026 (±8–10 minggu).
> Prinsip: **dua jalur paralel** — jalur koding (ketua) dan jalur lapangan (foto, izin
> toko, labeling — bisa didelegasikan). Koding tidak boleh menunggu lapangan.

## Timeline

| Minggu | Jalur koding | Jalur lapangan (paralel) |
|---|---|---|
| **1–2** (14–27 Jul) | **UI Mobile Web** — Beranda/Barang/Opname/Laporan nempel ke API yang sudah jadi. Akhir minggu 2: produk utuh bisa dipegang tim di HP | Izin 2–3 toko/gudang; mulai kumpul foto rak (target ≥500) — lihat `PANDUAN-DATASET.md` |
| **3–4** (28 Jul–10 Agu) | **Fine-tune YOLO** (WAJIB rulebook): pre-train SKU-110K → fine-tune dataset sendiri → tukar model. Lihat `PANDUAN-FINETUNE.md` | Labeling Roboflow (2 orang + QC ketua) |
| **5** (11–17 Agu) | **Deployment** (Railway/VPS + PWA) supaya tim tes remote; fine-tune CLIP kalau data cukup (opsional — skip boleh, tulis justifikasi) | Selesaikan sisa labeling |
| **6–7** (18–31 Agu) | **Tuning dari hasil uji** (threshold, parameter — tabel di CATATAN-TIM) | **Uji lapangan** di toko pilot: opname nyata vs hitung manual, catat akurasi |
| **8** (1–7 Sep) | **Submission**: pitch deck, video demo, proposal sesuai rulebook. Buffer ±1 minggu — JANGAN submit H-1 | Testimoni/feedback toko pilot buat pitch |

## Scope penyisihan (YAGNI)

**Wajib ada:** UI jalan di HP • model fine-tuned sendiri (+bukti kurva training) •
angka uji lapangan nyata • mode foto sebagai demo utama (paling stabil).

**Ditunda pasca-penyisihan:** TWA/Play Store • on-device inference • stitching antar-foto •
multi-user auth • integrasi POS.

## Risiko utama

1. **Izin toko & labeling molor** → mulai minggu INI, bukan setelah UI beres. Ini
   bottleneck waktu, bukan bottleneck koding.
2. Akurasi model zero-shot kurang di lapangan → guided mode + tuning threshold adalah
   jaring pengaman; fine-tune memperbaiki sisanya.
3. Waktu ketua habis di polish UI → patokan: fungsi > cantik sampai minggu 5; tweak
   visual = kerjaan tim setelah minggu 2.

## Status fondasi (sudah selesai, merged di main)

Pipeline video (YOLO+BoT-SORT+ReID+line-crossing) • Photo mode • Enrollment few-shot
CLIP • OCR expired Indonesia • Akuntansi (ledger, adjustment, opname manual, KPI,
export CSV) • JSON API lengkap • CI GitHub Actions • 56 test.
