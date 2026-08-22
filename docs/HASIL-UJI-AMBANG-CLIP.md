# Hasil uji ambang pencocokan CLIP (3 Agustus 2026)

> **Sudah direvisi.** Dokumen ini adalah catatan pengukuran 3 Agustus dan
> dibiarkan apa adanya sebagai riwayat. Kesimpulannya waktu itu, ambang 0,85,
> **tidak lagi berlaku**. Pengukuran kedua pada 22 Agustus memakai foto rak
> asli menurunkan ambang ke **0,80**; lihat bagian "Pengukuran kedua" di akhir
> berkas ini. Ringkasnya, peringatan "batas ATAS yang optimistis" di bawah
> ternyata benar dan menjatuhkan angkanya sendiri.

Ambang `0,75` di `matcher.match()` sebelumnya tidak pernah divalidasi — angka
yang ada cuma kasus tunggal (0,769 / 0,823 / 0,664), dan itu anekdot.

Diukur ulang dengan `scripts/ukur_ambang_clip.py` memakai foto enrollment yang
sudah terkelompok per produk lewat folder Drive. **Tanpa satu pun kotak
digambar** — kebenarannya sudah ada di struktur folder.

**12 produk, 104 foto**, leave-one-out: tiap foto diuji melawan galeri yang
tidak pernah memuat dirinya sendiri.

---

## Dua pekerjaan yang tarik-menarik

Ambang mengerjakan dua hal sekaligus, dan keduanya menginginkan arah berlawanan.

### A. Mengenali produk yang SUDAH di-enroll — mau ambang RENDAH

| Ambang | Benar | Salah | Ditolak | Presisi | Recall |
|---|---|---|---|---|---|
| ≤ 0,72 | **102** | 2 | 0 | 0,981 | 0,981 |
| **0,75** | 97 | 2 | 5 | 0,980 | 0,933 |
| 0,80 | 91 | 1 | 12 | 0,989 | 0,875 |
| 0,85 | 70 | 0 | 34 | 1,000 | 0,673 |
| 0,90 | 18 | 0 | 86 | 1,000 | 0,173 |

### B. Menolak produk yang BELUM di-enroll — mau ambang TINGGI

Diuji leave-one-**product**-out: satu produk dibuang dari seluruh galeri, lalu
fotonya harus ditolak.

| Ambang | Ditolak benar | **Lolos (salah)** | Akurasi tolak |
|---|---|---|---|
| 0,70 | 57 | 47 | 0,548 |
| **0,75** | 71 | **33** | 0,683 |
| 0,80 | 88 | 16 | 0,846 |
| 0,85 | 104 | **0** | 1,000 |

---

## Temuan utama

**Pada ambang produksi 0,75, satu dari tiga barang yang belum di-enroll
disangka produk lain.** 33 dari 104. Di laporan opname itu muncul sebagai
barang yang namanya salah — kesalahan paling merusak, karena terbaca meyakinkan
dan tidak ada tandanya.

Ini bagian yang selama ini tidak pernah diukur, dan justru tugas utama ambang.

**0,75 tidak optimal di kedua sumbu.** Dibanding 0,80 ia menukar 6 pengenalan
benar demi meloloskan 17 barang asing lebih banyak, dan malah menambah satu
salah tebak.

Rugi/untung tergantung berapa banyak barang di rak yang belum di-enroll:

| Rasio asing : terdaftar | Ambang terbaik |
|---|---|
| 1 : 1 | **0,80** |
| 3 : 1 (rak warung nyata) | **0,85** |

Warung mendaftarkan puluhan produk, sedangkan raknya memuat ratusan barang.
Jadi **barang asing jauh lebih banyak**, dan ambangnya semestinya naik.

**Keputusan: naik ke 0,85** (3 Agustus, `matcher.AMBANG_BAWAAN`).

Rekomendasi awalku 0,80 sebagai jalan tengah; yang dipilih 0,85, dan itu
konsisten dengan baris 3:1 di tabel atas — rak warung memang didominasi barang
yang belum di-enroll.

Bayarannya nyata dan disengaja: recall 0,933 → **0,673**, jadi sekitar sepertiga
barang terdaftar akan masuk "belum dikenali". Alasan pertukaran itu diterima:

| Jenis kesalahan | Tampak sebagai | Bisa dikoreksi pengguna? |
|---|---|---|
| Barang asing lolos | nama produk **salah** di laporan | tidak — terbaca meyakinkan, tanpa tanda |
| Barang terdaftar ditolak | "belum dikenali" | ya — pengguna melihat sendiri barangnya ada |

**Salah menyebut lebih mahal daripada tidak menyebut.**

Kalau uji lapangan menunjukkan terlalu banyak masuk "belum dikenali", turunkan
ke 0,80 — jangan kembali ke 0,75.

## Ambang bukan alat yang tepat untuk dua kebingungan ini

Dua salah tebak muncul di skor **tinggi**, di atas ambang mana pun yang masuk akal:

| Skor | Sebenarnya | Disangka |
|---|---|---|
| 0,823 | Fair and lovely, dermaglow | Dermaglow Lovely |
| 0,783 | Mie Goreng Sedapp | Indomie Kuah Soto Mie |

Keduanya **satu keluarga merek / satu kategori**. Menaikkan ambang untuk
membunuhnya berarti membuang puluhan pencocokan benar yang skornya lebih rendah.

Yang benar-benar menyelesaikan ini bukan ambang, melainkan:

1. **Guided mode** — aplikasi sudah punya `allowed_ids` di `match()`. Kalau
   pengguna menyatakan blok rak ini berisi produk apa saja, kebingungan
   antar-varian hilang sama sekali.
2. **Fine-tune CLIP** (metric learning) — mahal, dan `PANDUAN-FINETUNE`
   menandainya opsional. Belum layak sebelum detektornya beres.

## Batas pengukuran ini — baca sebelum mengutip angkanya

Foto enrollment adalah **close-up satu barang**. Di produksi yang di-embed
adalah **crop hasil detektor** dari foto rak: lebih kecil, lebih miring, lebih
banyak latar ikut terpotong.

Jadi angka di atas adalah **batas ATAS yang optimistis**. Pembacaannya: *kalau
di data serapi ini saja satu dari tiga barang asing sudah lolos, di produksi
pasti lebih buruk.*

Angka produksi yang sesungguhnya baru bisa diukur setelah uji lapangan dengan
model hasil fine-tune.

## Mengulang pengukuran

```bash
python -m scripts.ukur_ambang_clip --triase "<triase.json>" --triase-baru "<triase_baru.json>" --foto "<folder foto>"
```

Memakai `matcher.match()` asli dari repo, bukan tiruan — termasuk aturan
max-similarity (bukan rata-rata galeri).

---

# Pengukuran kedua (22 Agustus 2026) — ambang turun ke 0,80

Bagian "Batas pengukuran ini" di atas menulis bahwa angka 3 Agustus adalah
batas atas yang optimistis, dan angka sesungguhnya baru bisa diukur setelah
ada model hasil fine-tune. Model itu sekarang ada (`stoklens-yolo.pt`, dua
tahap, mAP50 0,827), jadi pengukurannya dijalankan.

## Cara

Satu foto rak lemari pendingin berisi **19 botol**. Tiga produk didaftarkan
lebih dulu lewat alur enrollment normal (foto close-up multi-sudut), lalu foto
raknya di-scan lewat `/api/scans-foto`. Setiap crop hasil detektor di-embed
ulang dan dibandingkan ke galeri ketiga produk itu memakai `matcher.match()`
asli.

Ini pengukuran pertama yang **crop-nya berasal dari detektor**, bukan dari foto
enrollment. Itulah bedanya dengan 3 Agustus.

## Hasil

| Potongan | Skor tertinggi | Putusan pada 0,85 | Kenyataan |
|---|---|---|---|
| Mizone | 0,888 | dikenali | benar |
| Teh pucuk | 0,833 | ditolak | salah tolak |
| Mizone kedua | 0,741 | ditolak | salah tolak |
| 16 botol asing | 0,613 tertinggi | ditolak | benar |

Recall produk terdaftar pada 0,85: **1 dari 3**. Pada 0,80: **2 dari 3**, tanpa
satu pun salah label.

## Bacaan

Crop dari rak lebarnya 63–110 px, miring, dan memantulkan cahaya kaca kulkas.
Skornya turun **0,05–0,11** dibanding foto enrollment. Itu persis pergeseran
yang diperingatkan bagian "Batas pengukuran ini", dan besarnya cukup untuk
melewati batas 0,85 dari sisi yang salah.

Yang menentukan keputusan bukan dua salah tolak itu, melainkan **jarak 0,613 ke
0,741**. Pemisahan antara produk terdaftar dan barang asing masih lebar, jadi
yang salah adalah letak ambangnya, bukan kemampuan CLIP membedakan. Ambang
0,80 berada di tengah jarak itu.

## Keterbatasan pengukuran ini, dan mereka nyata

- **Satu foto, tiga produk terdaftar.** Ini bukan sampel yang cukup untuk
  mengklaim recall. Ini cukup untuk membuktikan bahwa 0,85 menolak positif
  yang benar pada crop rak, dan itu saja yang diklaim.
- **16 botol asing** terlalu sedikit untuk menaksir laju salah label pada 0,80.
  Angka 84,6 % dari 3 Agustus tetap taksiran terbaik yang ada, dan taksiran itu
  berasal dari foto enrollment.
- Rak warung sungguhan memuat ratusan barang asing. Semakin banyak barang
  asing, semakin besar peluang salah satu menembus ambang.

## Yang harus diukur berikutnya

Ulangi pada rak warung penuh dengan ≥20 produk terdaftar. Bila ada barang asing
yang menembus **0,70**, ambang tetap sudah tidak cukup, dan gantinya adalah
ambang adaptif per produk (tiap produk punya ambangnya sendiri berdasarkan
sebaran kemiripan galerinya).
