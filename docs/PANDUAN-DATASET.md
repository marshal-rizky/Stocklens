# Panduan Pengumpulan Dataset StokLens

> Untuk anggota tim yang bertugas foto + labeling. Tidak perlu ngerti ML —
> ikuti panduan ini saja. Pertanyaan → tanya ketua di grup.

## Apa yang sedang kita bangun

Detektor "produk retail Indonesia" — model yang bisa menemukan **di mana ada barang**
di foto rak (kotak di sekeliling tiap dus/botol/sachet). Model TIDAK perlu tahu barang
itu merek apa — pengenalan merek dikerjakan komponen lain (CLIP). Karena itu labeling
kita cuma **satu kelas: `produk`**. Ini membuat kerjaan jauh lebih cepat.

**Target: 500–1000 foto berlabel dari 2–3 lokasi berbeda.**

## Tahap 1 — Izin lokasi (minggu ini!)

- Target: 2–3 toko grosir/gudang distributor kecil. Toko langganan keluarga = paling gampang.
- Tawaran imbal: "kami sedang bikin aplikasi hitung stok otomatis untuk lomba; boleh
  foto-foto rak? Nanti tokonya kami kasih hasil opname gratis + jadi pilot user pertama."
- Yang penting disampaikan: TIDAK memotret orang/kasir/pembeli, hanya rak barang.
- Catat: nama toko, kontak, hari yang boleh datang.

## Tahap 2 — Cara memotret

### Aturan wajib
1. **Resolusi penuh** kamera HP (≥12MP), **JANGAN zoom digital**.
2. **Tidak blur** — cek tiap foto sebelum lanjut; blur = buang.
3. **Tanpa wajah orang** di frame. Kalau tidak sengaja kena → hapus.
4. Format nama folder: `dataset/raw/<nama-toko>/<YYYY-MM-DD>/`

### Variasi yang HARUS ada (ini yang bikin model pintar)
Per rak, ambil 3–5 foto dengan variasi:

| Variasi | Contoh |
|---|---|
| Jarak | 50 cm / 80 cm / 120 cm |
| Sudut | Tegak lurus + miring ±15° kiri/kanan |
| Cahaya | Terang normal, agak redup, dekat jendela |
| Kepadatan | Rak penuh, setengah kosong, tumpukan tidak rapi |
| Jenis kemasan | Dus, botol, sachet gantung, plastik refill, kaleng — makin beragam makin bagus |
| Orientasi | Landscape DAN portrait |

Tambahkan juga ±20–30 foto rak kosong / hampir kosong (model perlu belajar "tidak ada
barang" juga).

### Jangan
- Jangan 50 foto rak yang sama dari posisi sama — 5 foto beragam > 50 foto kembar.
- Jangan edit/filter/crop foto.
- Jangan share foto ke luar tim (ada nama toko orang di dalamnya).

### Log
Isi sheet bersama (bikin di Google Sheets): tanggal • toko • jumlah foto • kondisi
cahaya • siapa yang moto. Ini bahan cerita "metodologi" di pitch.

## Tahap 3 — Upload & Labeling di Roboflow

1. Ketua bikin project Roboflow (tipe: **Object Detection**), invite via email.
2. Upload foto per batch lokasi.
3. **Satu kelas saja: `produk`.**

### Aturan labeling (KONSISTENSI = segalanya)
1. Kotak **ketat** ke tepi kemasan — jangan longgar, jangan motong.
2. Yang dilabel: barang yang **tampak depan (facing)** di baris terdepan rak.
3. Barang ketutupan sebagian: masih terlihat ≥50% → label; ketutupan >70% → SKIP.
4. Barang kepotong tepi foto: terlihat ≥50% → label.
5. Barang baris belakang yang cuma kelihatan pucuknya → SKIP (kita menghitung facing).
6. Ragu? Screenshot → tanya grup → keputusan dicatat di sheet supaya semua labeler
   ikut aturan yang sama.

### Estimasi kerja (realistis)
1 foto rak ±20–40 kotak ≈ 2–3 menit. 500 foto ≈ 20–40 jam-orang →
**2 orang × 1,5 jam/hari × 2 minggu = selesai.** Jangan maraton 8 jam — kualitas drop.

### QC (ketua)
Sampling 10% dari tiap labeler tiap 2–3 hari. Kotak longgar / barang kelewat →
feedback langsung, jangan tunggu selesai semua.

## Tahap 4 — Export

Ketua yang pegang: Roboflow → Generate → split 80/10/10 (train/valid/test) →
export format **YOLO** → lanjut ke `PANDUAN-FINETUNE.md`.

Augmentasi di Roboflow: cukup brightness ±15% dan blur ringan 1px. Mosaic/rotasi
TIDAK usah (ultralytics sudah melakukan augmentasi sendiri saat training).

## Checklist selesai

- [ ] ≥500 foto, ≥2 lokasi, semua variasi tabel di atas terwakili
- [ ] ≥20 foto rak kosong/hampir kosong
- [ ] Semua terlabel 1 kelas `produk`, QC lolos
- [ ] Sheet log terisi
- [ ] Export YOLO 80/10/10 tersimpan di Drive tim (JANGAN commit ke git)
