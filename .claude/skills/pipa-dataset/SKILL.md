---
name: pipa-dataset
description: Jalankan pipa dataset StokLens dari foto mentah Drive sampai siap-review di Roboflow — auto-label pakai Grounding DINO, lembar kontak untuk triase manusia, unggah dengan split train/test yang benar. Pakai ketika ada gelombang foto baru dari tim, atau saat diminta "auto-label", "kirim ke Roboflow", "siapkan dataset".
---

# Pipa dataset StokLens

Satu perintah dari foto mentah sampai batch siap dibetulkan di Roboflow.

## Perintah

```bash
pip install "transformers>=4.44" roboflow

python -m scripts.pipa_dataset --foto "<folder foto>" --triase "<triase.json>" --triase-baru "<triase_baru.json>" --keluar "<folder hasil>" --proyek stoklens-produk-warung
```

Tulis **satu baris**. `\` penyambung baris adalah sintaks POSIX; di `cmd.exe` ia
tidak menyambung apa pun dan ikut terbaca sebagai bagian path.

Tanpa `--jalankan` pipa berhenti sebelum mengunggah. Itu bawaannya, bukan galat
— langkah 3 memang menunggu mata manusia.

## Empat langkah

| # | Skrip | Hasil |
|---|---|---|
| 1 | `scripts.testset` | daftar foto uji, dikunci deterministik (1 dari 4 foto rak per domain) |
| 2 | `scripts.autolabel_grounding` | kotak awal dari Grounding DINO, ambang 0,25 |
| 3 | `scripts.lembar_kontak` | lembar kontak 24 foto/lembar, yang mencurigakan ditandai merah |
| 4 | `scripts.kirim_roboflow` | unggah, split train/test benar, `is_prediction=True` |

## Yang WAJIB dipahami sebelum menjalankan

**Foto uji tidak boleh ikut dilatih.** `baseline_detektor.py` sudah merekam
angka "sebelum" pada 44 foto tertentu. Kalau foto itu masuk `train`, model
dilatih pada foto ujinya sendiri dan seluruh perbandingan tidak sah — dan
**tidak ada yang akan gagal**; angkanya justru naik dan terlihat meyakinkan.
Pipa ini memasang penjaganya otomatis; jangan jalankan langkah-langkahnya
terpisah tanpa `--daftar-uji`.

**Kotaknya tebakan mesin.** Dikirim dengan `is_prediction=True` supaya masuk
sebagai prediksi menunggu review, bukan ground truth. `add_to_dataset` tetap
false — manusia yang meloloskan lewat Annotate → Accept into dataset.

**Buang gambar yang sudah bergaris kotak sebelum mulai.** Tangkapan layar hasil
scan dan gambar contoh berlabel sering menumpuk di folder foto. Kalau ikut
terlatih, model belajar mengenali persegi hijau, bukan produk. Terjadi 2
Agustus: 17 dari 43 berkas di folder demo ternyata gambar diagnostik.

## Mutu kotak terbelah dua — itu sebabnya langkah 3 ada

Diukur di 171 foto (2 Agustus, 2090 kotak, median 10/foto):

| Jenis foto | Hasil |
|---|---|
| Rak minimarket rapi | sangat baik, satu kotak per barang (sampai 47 kotak) |
| Etalase warung padat | **buruk** — kotak raksasa menelan satu baris rak |
| Pemandangan jalan | seharusnya tidak ada di bucket detektor sejak awal |
| Close-up satu barang | benar |

Penyaring isi otomatis pakai CLIP **sudah dicoba dan gagal**: seluruh skor
berdesak 0,246–0,393, dan foto pemandangan jalan yang sudah diverifikasi mata
mendapat skor tepat di median. Jangan coba ulang pendekatan itu tanpa ide baru.

Yang tersisa otomatis cuma tanda **pola kotak-raksasa** (≤6 kotak tapi ada yang
>25 % frame) — berbasis struktur, bukan tebakan makna.

## Sesudah pipa selesai

1. Buka Roboflow → Annotate → batch yang baru
2. Betulkan: **tambah kotak yang terlewat**, gabung serpihan jadi satu kotak per
   barang, hapus kotak raksasa. Renceng tetap 1 sachet = 1 kotak
3. QC 10 % per pelabel
4. Accept into dataset → Generate versi → fine-tune lokal (`PANDUAN-FINETUNE`)

Rinciannya: `docs/PANDUAN-DATASET.md` Tahap 3, `docs/PANDUAN-FINETUNE.md` Step 1.6.
