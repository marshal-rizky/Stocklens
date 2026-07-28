# Panduan Pengumpulan Dataset StokLens

> Untuk anggota tim yang bertugas foto + labeling. Tidak perlu ngerti ML —
> ikuti panduan ini saja. Pertanyaan → tanya ketua di grup.

## Apa yang sedang kita bangun

Detektor "produk retail Indonesia" — model yang bisa menemukan **di mana ada barang**
di foto rak (kotak di sekeliling tiap dus/botol/sachet). Model TIDAK perlu tahu barang
itu merek apa — pengenalan merek dikerjakan komponen lain (CLIP). Karena itu labeling
kita cuma **satu kelas: `produk`**. Ini membuat kerjaan jauh lebih cepat.

**Target: 500–700 foto BERLABEL dari 2–3 lokasi berbeda.** Foto yang diambil boleh
jauh lebih banyak — lihat §"Berapa banyak" di bawah, memotret dan melabeli itu dua
biaya yang sangat berbeda.

## Foto harus dari WARUNG MADURA, bukan grosir

Ini keputusan yang gampang salah dan mahal kalau terlanjur.

Model kita sudah di-pre-train di **SKU-110K**, dataset rak **supermarket** (11 ribu
foto, rata-rata 155 objek per gambar). Dari situ model sudah pandai soal bagian
tersulit: mendeteksi objek kecil yang berjejalan rapat. Tugas dataset kita cuma satu
— mengajari **kondisi lokal yang tidak ada di supermarket**:

| Ciri warung Madura | Ada di SKU-110K? |
|---|---|
| **Sachet gantung (renceng)** | Hampir tidak ada. Untaian vertikal yang saling tumpuk — bentuk paling asing bagi model, dan paling khas warung |
| Cahaya bohlam hangat / remang | Tidak. Supermarket neon terang merata |
| Barang non-produk berserakan di frame | Tidak. Rak supermarket bersih |
| Rak improvisasi (papan kayu, kardus, etalase kaca) | Tidak. Gondola standar |
| Ruang sempit, tidak bisa mundur 80 cm | Tidak. Lorong supermarket lebar |

**Kalau foto diambil di grosir, kita menutup satu jurang domain lalu membuka jurang
kedua** — model jadi pandai di grosir, lalu tetap gagal di warung, yaitu tempat
produk ini sebenarnya dipakai dan tempat juri membayangkannya.

## Tahap 1 — Izin lokasi (minggu ini!)

- Target: **2–3 warung Madura / toko kelontong kecil**. Warung langganan = paling gampang.
  Kalau ada kesempatan grosir, ambil sebagai bonus, bukan sebagai sumber utama.
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

### Kondisi foto — aturan keras (dari analisis 18 Juli)

Ini bagian yang paling sering salah dan paling mahal akibatnya. Dua jenis foto,
dua aturan berbeda — jangan dicampur.

**Foto untuk DATASET DETEKTOR (YOLO):**

| Wajib | Kenapa |
|---|---|
| Foto **rak asli** — kayu, kaca, besi; penuh maupun setengah kosong | Model belajar "barang rapat di rak", bukan "barang di ruang kosong" |
| Rak kaca dapat **sampel ekstra** (+30–50% dari jatah rak biasa) | Pantulan dan barang tembus pandang jauh lebih sulit; porsi normal tidak cukup |

| Dilarang | Kenapa |
|---|---|
| Foto barang **ditata di meja** | Hampir tidak berguna — kepadatan & oklusinya tidak pernah muncul di gudang |
| **Foto stock internet / marketplace** | MERUSAK. Latar putih bersih tidak pernah ada di gudang; model belajar bias itu lalu gagal di rak asli. Juga melanggar ToS/hak cipta → risiko diskualifikasi (rulebook #17) |

**Foto untuk ENROLLMENT (galeri CLIP per barang):**

Aturan tunggal: **potret di kondisi yang sama dengan saat nanti di-scan.**

- Jarak mirip jarak scan, **cahaya toko yang sama** (jangan bawa pulang lalu foto di rumah)
- 3–5 sudut per barang, termasuk sudut menyerong — bukan cuma tampak depan lurus
- **Jangan pakai foto stock/marketplace.** Desain kemasannya sering versi lama →
  match gagal padahal barangnya benar

Urutan faktor perusak match, dari yang paling parah: (1) beda skala/ketajaman,
(2) beda cahaya/suhu warna, (3) beda sudut, (4) latar/rak, (5) foto stock internet.

> Jaring pengaman kalau enrollment terlanjur tidak ideal: fitur **enroll-dari-scan**
> — item `unknown` di laporan bisa ditap dan diberi nama, crop-nya masuk galeri
> dalam kondisi scan yang persis. Itu perbaikan, **bukan** alasan untuk memotret asal.

### Log
Isi sheet bersama (bikin di Google Sheets): tanggal • toko • jumlah foto • kondisi
cahaya • siapa yang moto. Ini bahan cerita "metodologi" di pitch.

## Berapa banyak — memotret ≠ melabeli

Dua biaya yang sangat berbeda, sering dicampur dan bikin salah rencana.

**Memotret hampir gratis. Potret sebanyak yang sempat.** Kelebihannya tetap berguna:
jadi test set generalisasi, jadi foto enrollment, dan jadi cadangan kalau sebagian
ternyata blur.

**Melabeli mahal, dan di situ lomba bisa habis.** Pakai angka di §"Estimasi kerja":

| Foto berlabel | Jam-orang | 2 orang × 1,5 jam/hari |
|---|---|---|
| 500 | 20–40 | ±2 minggu |
| **2000** | **80–160** | **±8 minggu** ❌ tidak muat di sisa waktu |

Dan lebih banyak label belum tentu lebih akurat. Karena pre-train sudah mengajari
"produk berjejalan", yang kurang tinggal kondisi lokal — dan untuk itu **keragaman
jauh lebih penting daripada jumlah**. 500 foto beragam dari 3 warung mengalahkan
2000 foto mirip dari 1 warung.

**Rencana yang muat:** potret sebanyak mungkin → labeli 500–700 pilihan paling
beragam (pakai auto-labeling di bawah) → **sisihkan seluruh foto dari SATU warung
tanpa dilabeli dan tanpa ikut training**, sebagai uji generalisasi (Step 3
`PANDUAN-FINETUNE.md`).

### Ukur jurangnya lebih awal, jangan tunggu 500

Begitu ada **±50 foto warung berlabel**, jalankan model pre-train di situ dan catat
mAP50-nya. Bandingkan dengan 0,868 yang didapat di validasi SKU-110K. Selisihnya =
ukuran jurang supermarket→warung, dan angka itu menjawab pertanyaan "berapa foto
lagi yang sebenarnya kita butuh" dalam hitungan hari, bukan minggu. Angka
sebelum/sesudah ini juga bahan proposal yang kuat.

## Di mana menaruh foto (beberapa orang, HP berbeda)

### ⛔ JANGAN kirim foto lewat WhatsApp

Ini penghancur dataset nomor satu. WhatsApp mengompres foto ke ±1 MP, sedangkan
aturan di atas mewajibkan resolusi penuh ≥12 MP. **Foto yang sudah lewat WA rusak
permanen dan tidak bisa dipulihkan** — dan biasanya baru ketahuan setelah ratusan
foto terkumpul. Berlaku juga untuk Telegram mode "compress" dan Google Photos
dengan setelan "Storage saver".

Pakai **Google Drive** (aplikasi Drive, BUKAN Google Photos — Drive tidak mengompres).
Upload langsung dari HP masing-masing ke folder bersama.

### Struktur folder

```
dataset/raw/<nama-warung>/<YYYY-MM-DD>/<inisial-pemotret>/
```

`<inisial-pemotret>` itu bukan hiasan: **nama file dari HP berbeda pasti
bertabrakan.** Tiga iPhone sama-sama menghasilkan `IMG_0001.jpg` dengan isi berbeda;
begitu digabung ke satu folder, sebagian tertimpa diam-diam dan tidak ada yang sadar.
Memisahkan per pemotret mencegahnya tanpa perlu rename manual.

### Yang perlu dicek sebelum semua orang upload

- **Kuota Drive.** ±4 MB per foto → 2000 foto ≈ **8 GB**. Drive gratis 15 GB dan
  dipakai bareng Gmail. Cek sisa kuota pemilik folder dulu, jangan mentok di tengah.
- **Jangan hapus EXIF.** Tanggal dan tipe HP berguna untuk sheet log dan cerita
  metodologi di proposal.
- **Akses per undangan, bukan "siapa pun dengan link".** Foto warung memuat nama
  usaha orang — lihat `CARA-KERJA-TIM.md` §8.

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

### Sachet gantung (renceng) — putuskan SEKARANG, jangan di tengah jalan

Ini bentuk paling khas warung Madura dan paling tidak dikenal model (SKU-110K
nyaris tidak punya contohnya). Pertanyaannya: **satu renceng isi 10 sachet itu
1 kotak atau 10 kotak?**

**Aturan kita: 1 sachet = 1 kotak.** Alasannya bukan soal labeling, tapi soal produk —
warung menjual dan menghitung stoknya **per sachet**, bukan per renceng. Kalau model
menghitung per renceng, angka di laporan opname tidak akan cocok dengan cara pemilik
warung menghitung, dan seluruh fitur selisih stok jadi tidak bermakna baginya.

Konsekuensi yang harus diterima:
- Melabeli renceng itu lambat — satu renceng bisa 10–12 kotak kecil bertumpuk.
- Sachet yang ketutupan >70% oleh sachet di depannya tetap di-SKIP (aturan 3).
- Kalau di uji lapangan hasilnya kacau, opsi cadangan: perlakukan renceng sebagai
  satu objek lalu kalikan jumlah sachet per renceng saat enrollment. **Jangan ganti
  aturan di tengah labeling** — dataset campuran lebih buruk daripada dua-duanya.

Pastikan ada **cukup banyak foto renceng** di dataset. Kalau warung penuh renceng
tapi foto yang diambil semua rak dus, model tidak akan pernah belajar bentuk itu.

### Estimasi kerja (realistis)
1 foto rak ±20–40 kotak ≈ 2–3 menit. 500 foto ≈ 20–40 jam-orang →
**2 orang × 1,5 jam/hari × 2 minggu = selesai.** Jangan maraton 8 jam — kualitas drop.

Angka itu berlaku kalau menggambar dari nol. **Jangan.** Pakai auto-labeling di bawah.

## Auto-labeling — MENGOREKSI, bukan menggambar dari nol

Sejak 28 Juli kita punya model hasil pre-train SKU-110K dengan **mAP50 0,868** di
foto rak retail. Model itu bisa menggambar kotak duluan di foto kalian; tim tinggal
**mengoreksi** yang salah. Estimasi kerja turun drastis: **20–40 jam-orang → 3–5 jam.**

Ini yang membuat melabeli 500–700 foto muat di sisa waktu.

### Cara pakai

Ketua menjalankan ini sekali atas semua foto mentah, lalu meng-upload hasilnya ke
Roboflow sebagai anotasi awal:

```python
# Jalankan dari mana saja. Ganti dua path di bawah.
from ultralytics import YOLO


def main():
    model = YOLO(r"C:\Users\<ketua>\StokLens-training\pretrain_sku110k\weights\best.pt")
    model.predict(
        source=r"D:\dataset\raw",   # folder foto mentah (boleh bersarang)
        save_txt=True,              # tulis anotasi format YOLO
        save_conf=False,            # Roboflow tidak butuh kolom confidence
        conf=0.25,                  # ambang rendah: lebih baik kelebihan kotak
        imgsz=640,
        stream=True,                # jangan tahan semua hasil di RAM
        project=r"D:\dataset\autolabel",
        name="ronde1",
    )


if __name__ == "__main__":
    main()
```

Hasilnya ada di `autolabel/ronde1/labels/*.txt` — satu file per foto, format YOLO,
langsung bisa di-upload ke Roboflow bareng gambarnya sebagai anotasi awal.

### Kenapa `conf=0.25`, bukan angka default yang lebih tinggi

**Menghapus kotak jauh lebih cepat daripada menggambar kotak.** Ambang rendah membuat
model memberi kotak berlebih; labeler tinggal menghapus yang salah. Ambang tinggi
menghasilkan foto yang bolong, dan mengisi lubang itu berarti kembali menggambar
manual — persis yang mau kita hindari.

### Yang WAJIB tetap dikerjakan manusia

Auto-label bukan pengganti QC. Model ini belum pernah melihat warung Madura, jadi
justru di titik-titik inilah ia paling sering salah — dan titik-titik ini pula yang
paling menentukan akurasi akhir:

- **Sachet gantung (renceng).** Hampir pasti kacau — kotaknya akan menggabung
  beberapa sachet jadi satu, atau melewatkannya sama sekali. Periksa satu per satu.
- **Barang di etalase kaca.** Pantulan sering dikira objek.
- **Rak remang / backlight.** Deteksi menghilang di area gelap.
- **Barang non-produk** (kursi, kardus kosong, kipas) yang terlanjur dikotaki.

Aturan QC ketua tetap berlaku: sampling 10% tiap labeler tiap 2–3 hari.

### Setelah dataset sendiri jadi

Ronde kedua auto-labeling memakai model hasil fine-tune (bukan pre-train) akan jauh
lebih akurat, karena sudah pernah melihat warung. Kalau masih ada sisa foto yang
belum dilabeli, kerjakan ronde itu — bukan ronde pertama diulang.

### QC (ketua)
Sampling 10% dari tiap labeler tiap 2–3 hari. Kotak longgar / barang kelewat →
feedback langsung, jangan tunggu selesai semua.

## Tahap 4 — Export

Ketua yang pegang: Roboflow → Generate → split 80/10/10 (train/valid/test) →
export format **YOLO** → lanjut ke `PANDUAN-FINETUNE.md`.

Augmentasi di Roboflow: cukup brightness ±15% dan blur ringan 1px. Mosaic/rotasi
TIDAK usah (ultralytics sudah melakukan augmentasi sendiri saat training).

## Checklist selesai

- [ ] ≥500 foto berlabel, ≥2 lokasi, semua variasi tabel di atas terwakili
- [ ] **Lokasinya warung Madura / kelontong kecil**, bukan grosir
- [ ] **Cukup banyak foto sachet gantung (renceng)** — bentuk paling asing bagi model
- [ ] ≥20 foto rak kosong/hampir kosong
- [ ] Tidak ada satu pun foto meja / foto stock internet yang lolos ke dataset
- [ ] Tidak ada foto yang pernah lewat WhatsApp/Telegram-compress
- [ ] Satu warung disisihkan utuh sebagai uji generalisasi (tidak ikut training)
- [ ] Aturan renceng (1 sachet = 1 kotak) dipatuhi konsisten oleh semua labeler
- [ ] Semua terlabel 1 kelas `produk`, QC lolos
- [ ] Sheet log terisi
- [ ] Export YOLO 80/10/10 tersimpan di Drive tim (JANGAN commit ke git)
