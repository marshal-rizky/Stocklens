# Hasil uji ambang pencocokan CLIP (3 Agustus 2026)

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
