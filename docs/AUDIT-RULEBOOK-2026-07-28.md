# Audit StokLens — AIC COMPFEST 18

> Dibuat 2026-07-28. Sumber: rulebook resmi `[AIC] AI Innovation Challenge.pdf` (28 hal),
> repo `marshal-rizky/Stocklens` (commit `612e85f` di main), riset web.

---

## 0. RINGKASAN EKSEKUTIF

Kode kalian **bagus** — di atas rata-rata proyek lomba mahasiswa. Yang bermasalah
bukan engineering-nya, tapi **perencanaan terhadap rulebook**.

1. **Deadline penyisihan 25 Agustus 2026, bukan September.** ROADMAP.md
   menjadwalkan submission 1–7 September — **7–13 hari SETELAH deadline.**
   Sisa waktu nyata: **28 hari**.
2. **45% bobot nilai ada di deliverable yang belum disentuh** (video promosi 15%,
   proposal 15%, kesiapan MVP 15%).
3. **MVP kalian OVERBUILT, dan overbuilt dinilai negatif secara eksplisit.**

Peluang lolos 8 besar bila eksekusi 90–95%: **sedang-ke-baik**.
Juara 1: **rendah-ke-sedang**. Rincian di §5.

---

## 1. RULEBOOK vs DOKUMEN KALIAN

| Item | Docs kalian | Rulebook | Dampak |
|---|---|---|---|
| Deadline penyisihan | "±September 2026" | **25 Agu 2026, 23.55 WIB** | KRITIS |
| Jadwal submission | Minggu 8 (1–7 Sep) | Lewat deadline | KRITIS |
| Sisa waktu | "±8–10 minggu" | 28 hari | KRITIS |
| Registrasi | tidak dicatat | Batch 2 tutup 18 Juli | Verifikasi |
| Technical Meeting | tidak dicatat | 18 Juli (lewat) | Verifikasi |
| AIC Talks | tidak dicatat | 25 Juli (lewat) — bonus 1.5% | Hangus? |
| Deliverable | 3 item | 4 item (§2) | Kurang 1 |
| Deployment cloud | Minggu 5: Railway/VPS + PWA | **Tidak wajib**, final cukup localhost | Buang |
| Ukuran tim | tidak dicatat | **Wajib 3–5 orang** | Verifikasi |
| docker compose | tidak ada | **WAJIB** | Belum ada |

### Verifikasi HARI INI
- [ ] Tim terdaftar & "TIM TERVERIFIKASI" sebelum 18 Juli?
- [ ] Anggota 3–5 orang WNI, usia ≤25, pelajar/mahasiswa aktif hingga 27 Sep 2026?
- [ ] Hadir AIC Talks 25 Juli + isi presensi? (bonus 1.5%)
- [ ] Dapat VPS/GPU credits gratis (30 pendaftar pertama)?
- [ ] Discord AIC, nickname `[Nama Tim] - [Nama]`?

---

## 2. DELIVERABLE PENYISIHAN (25 Agu, 23.55 WIB)

| # | Deliverable | Spesifikasi | Status |
|---|---|---|---|
| 1 | Repo GitHub **public** | README setup guide + **docker compose** | ⚠️ file lengkap sejak 28 Jul sore, **verifikasi jalan-sungguhan belum** |
| 2 | Video **proof of work** | ≤7 mnt, YouTube **unlisted**, judul `COMPFEST 18 AIC: PROOF OF WORK - [Tim] - [Proyek]` | ❌ |
| 3 | Video **promosi inovasi** | ≤5 mnt, YouTube **public**, MP4 ≥720p, judul `COMPFEST 18 AIC: [Tim] - [Proyek]` | ❌ |
| 4 | **Proposal PDF** | ≤20 hal (di luar cover/pustaka/lampiran) | ❌ |

Boleh submit berkali-kali, **dinilai submisi terakhir**. Tidak submit = mundur.

### Aturan video proof of work yang gampang bikin gugur
- Wajib **double screen**: terminal + aplikasi, **plus timestamp**
- **DILARANG KERAS memotong (cut).** Hanya fast-forward + voice over
- Wajib jujur: tunjukkan fitur belum jalan/buggy, jelaskan statusnya
- Semua fitur di video promosi **harus ada** di video proof of work
- Panitia cross-check

### Conventional Commits — WAJIB
Rulebook mewajibkan `feat:` / `fix:` / `refactor:`. Repo mayoritas **sudah patuh** ✅.
Satu pelanggaran: `612e85f` "Update CATATAN-TIM.md" (edit via web GitHub).

### Standby Discord
**9 & 10 Sep, 20.00** — panitia bisa minta **live demo**, wajib jawab ≤2 jam.
Aplikasi harus benar-benar jalan, bukan cuma lolos test.

---

## 3. KRITERIA PENILAIAN + SKOR JUJUR

| Kriteria | Bobot | Posisi | Estimasi |
|---|---|---|---|
| Implementasi Teknologi & Kematangan Arsitektur | **25%** | Sangat kuat | 20–23 |
| Orisinalitas dan Dampak Sosial | **20%** | Kuat, ada pesaing | 14–17 |
| Kesiapan MVP untuk Babak Final | **15%** | **Overbuilt — dinilai negatif** | 9–12 |
| Video Promosi | **15%** | Belum ada | 0–12 |
| Kualitas Proposal & Proses Pengembangan | **15%** | Belum ada, bahan melimpah | 0–14 |
| Relevansi dengan Tema | **10%** | Smart Logistics, pas | 9–10 |
| Business Value & Governance (BONUS) | 3.5% | Belum ada | 0–3 |
| AIC Talks (BONUS) | 1.5% | Sudah lewat | 0 atau 1.5 |
| **TOTAL** | **105%** | | **52–92** |

### 3.1 Implementasi & Arsitektur (25%) — kekuatan utama
Juri tanya: *"Seberapa modular arsitektur — apakah komponen AI, backend, dan
frontend terpisah dengan bersih?"*

Persis yang kalian lakukan. Aturan "logika murni dipisah dari wrapper model berat"
membuat `torch`/`ultralytics`/`easyocr` hanya di-import di `embedder.py` dan di
dalam fungsi (`scan.py:54`, `photo.py:52`, `ocr.py:8`). Seluruh suite test cepat
jalan **tanpa** torch — CI GitHub Actions membuktikannya tiap PR (deps-nya sengaja
tidak memasang torch stack). Bukti modularitas yang bisa didemokan, bukan diklaim.

### 3.2 Orisinalitas (20%) — kuat, tapi jangan lebay
Pesaing nyata dari riset web:
- **WarungVision** — AI "melihat" stok di rak untuk UMKM, pakai Gemini/OpenAI/Kolosal
- **Warung Bakso (AuliaSoft)** — "Smart AI Stock Opname", foto → entri massal
- Puluhan app stock opname barcode (Bee, Kledo, HashMicro)

**Jangan klaim "belum ada yang begini".** Klaim yang jujur DAN kuat:
1. Enrollment few-shot, **nol retraining** di lapangan
2. Menghitung **facing di rak**, bukan OCR dokumen laporan
3. Anti dobel-hitung berlapis (ReID + track_buffer + line-crossing)
4. Self-improving lewat enroll-dari-scan
5. **Jalan lokal, tanpa API pihak ketiga** — biaya per-scan nol, data tak keluar
   toko. Pembeda tajam vs pesaing yang bergantung Gemini/OpenAI.

### 3.3 Kesiapan MVP (15%) — RISIKO TERBESAR YANG BISA DIKENDALIKAN
Rulebook, huruf tebal: ruang lingkup **WAJIB HANYA SAMPAI**:
1. **Frontend**: hanya alur inti — terima input, tampilkan output AI. *"tidak perlu
   dashboard analitik tingkat lanjut, sistem otentikasi kompleks, atau halaman
   riwayat penggunaan."*
2. **Backend**: hanya sinkron. Tidak perlu background jobs, **automated data
   logging**, DB terdistribusi. Harus jalan lokal via **docker compose**.
3. **Model**: hanya core inference, parameter statis. Tidak perlu auto-tuning,
   bulk testing scripts, **loop umpan balik otomatis**.

Kriteria: *"Apakah ruang lingkup MVP sudah tepat (**tidak overbuilt** atau underbuilt)?"*

**Yang melewati batas:**

| Fitur | Batasan yang disentuh |
|---|---|
| Beranda KPI (nilai stok, shrinkage, rugi expired, stok menipis) | "dashboard analitik tingkat lanjut" |
| Riwayat opname / daftar laporan | "halaman riwayat penggunaan" |
| Export CSV | di luar alur inti |
| Kartu stok + ledger + penyesuaian | "automated data logging" |
| Opname manual (checklist) | bukan alur AI |

`enroll-dari-scan` **kemungkinan aman** — rulebook melarang loop **otomatis**,
milik kalian dipicu tap user. Tetap siapkan jawabannya.

**Bukan berarti hapus.** Artinya:
- Di proposal & video, bingkai alur inti = *enroll → scan → laporan selisih*
- Video proof of work: demokan alur inti dulu dan paling lama
- Siapkan kalimat: *"Ledger diperlukan karena selisih stok tak bermakna tanpa
  angka tercatat sebagai pembanding — bagian dari output core inference."*
- **Jangan bangun apa pun baru di luar alur inti.** Backlog #3 → **batalkan**

### 3.4 Video Promosi (15%) — bobot setara arsitektur, effort 1/50
Juri menilai: komunikasi masalah+solusi; cerita proses perancangan (ide →
eksekusi) dengan storytelling; menarik untuk stakeholder; konten lengkap.

Bahan storytelling kalian **sangat kuat dan belum dipakai**: keputusan desain +
alasannya, kegagalan terdokumentasi (dedup embedding ditolak, guard test kelewat
lebar dua kali), analisis 18 Juli soal kenapa enrollment gagal-match.

### 3.5 Proposal (15%) — hampir gratis
Struktur wajib: Nama & Judul; Latar Belakang; Tujuan & Manfaat; Metodologi (alur
dapat dataset, alur pengembangan model tiap feature, alur integrasi model ke
environment kode); metode pendukung keputusan; Kesimpulan.

Juri: *"Apakah decision making dijelaskan dengan alasan berbasis data atau
analisis?"* dan *"Apakah cerita pengembangan mencerminkan proses iteratif yang
reflektif, bukan sekadar deskripsi fitur?"*

**CATATAN-TIM §"Keputusan desain penting + ALASANNYA" adalah jawabannya, sudah
jadi.** PANDUAN-DATASET = alur dataset. PANDUAN-FINETUNE = alur model.
Keunggulan tak sengaja — eksploitasi.

### 3.6 Business Value (bonus 3.5%)
1 halaman: harga per toko, biaya marginal ~0 (inference lokal), banding vs
RFID/barcode, etika (tidak memotret orang — sudah di PANDUAN-DATASET), privasi.

---

## 4. AUDIT KODE & PROSES

### 4.1 Yang bagus (pertahankan)
- Pemisahan logika murni vs wrapper model — seluruh suite test jalan tanpa torch
- Injectable detector/embedder → CI tanpa GPU
- Dokumentasi keputusan **beserta alasan penolakan** — langka
- Git: branch per fitur, PR, CI wajib hijau, Conventional Commits
- Test guard untuk aturan arsitektur
- Plan doc per fitur dengan status unit + catatan review

### 4.2 Utang teknis

> Kolom Status diperbarui 2026-07-28 sore, setelah sebagian temuan langsung dieksekusi.

| Item | Status |
|---|---|
| PR #19 konsolidasi ledger | ✅ **Beres** — sudah merged ke main (`514f7bb`) |
| Backlog B (aturan kondisi foto) | ✅ **Beres** — masuk `PANDUAN-DATASET.md` §"Kondisi foto" |
| Backlog #3 export CSV per-laporan | ✅ **Beres** — ditandai DIBATALKAN di `BACKLOG.md` |
| Backlog #7 N+1 | ✅ **Beres** — klaim `/api/dashboard` dikoreksi di `BACKLOG.md`; hanya `/api/scans` yang N+1 (`api.py:214`) |
| Jumlah test di docs | ✅ **Beres** — angka pastinya dihapus dari semua docs, diganti perintah `pytest -q --collect-only`. Menyamakan tiga angka salah cuma menunda masalah; angkanya berubah tiap PR |
| Header CATATAN-TIM | ✅ **Beres** — jadi 2026-07-28 |
| `docker compose` | ⚠️ **Separuh** — `Dockerfile` + `docker-compose.yml` + `.dockerignore` + panduan README sudah ada, tapi belum pernah di-build sungguhan. Wajib diverifikasi satu orang |
| CLI di README tidak jalan | ✅ **Beres** — `python scripts/demo_scan.py` selalu gagal (`ModuleNotFoundError`); seluruh docs & docstring diganti ke `python -m scripts.demo_scan`. Bug lama, baru ketahuan saat review docker |
| `STATUS.md` | ✅ **Beres** — dibuat, dirujuk `CARA-KERJA-TIM.md` §6 |
| Deprecation | ⬜ Belum — `starlette.testclient` minta `httpx2`. Tidak memblokir, biarkan sampai penyisihan lewat |

### 4.3 Risiko proses yang terbukti dua kali
Konflik semantik: dua branch hijau sendiri-sendiri, git merge bersih, CI merah
setelah merge. Terjadi PR #16↔#20, lalu memakan korban PR #19.
Sudah didokumentasikan, tapi belum jadi **aturan yang memaksa**.

### 4.4 Sub-agent-driven development
Pola "implement → spec review → quality review → fix loop" menghasilkan temuan
nyata (Unit 4: 4 Important + 2 Minor lewat 3 putaran, satu di antaranya regresi
yang lahir dari fix sebelumnya).

**Kelemahan untuk tim:** semua 9 PR di-author satu orang, tanpa reviewer manusia
lain. Aturan tertulis "minimal 1 orang lain melihat sebelum merge" **tidak pernah
dijalankan**.

---

## 5. PELUANG MENANG

Asumsi: eksekusi 90–95%, tim 3–5 aktif, terdaftar sah.

| Target | Peluang | Alasan |
|---|---|---|
| Lolos 8 besar | **55–70%** | Arsitektur & dokumentasi di atas rata-rata; risiko overbuilt + deliverable telat |
| Juara 3 | **20–30%** | Butuh video & proposal bagus, bukan cuma kode |
| Juara 1 | **8–15%** | Butuh angka uji lapangan + pitch kuat + hackathon 10 jam solid |

Bukan angka statistik — penilaian berdasar bobot rubrik vs kondisi repo.

### Menaikkan peluang (urut efisiensi)
1. ~~Perbaiki jadwal ke 25 Agu~~ ✅ (`ROADMAP.md` direvisi total)
2. Video promosi + proposal — 30% bobot, bahan sudah ada ← **prioritas nomor 1 sekarang**
3. Fine-tune YOLO — wajib rulebook, mengisi 25% implementasi
4. Angka uji lapangan nyata — mengubah pitch dari klaim jadi bukti
5. ~~docker compose + README~~ ✅
6. ~~Bingkai ulang scope agar tidak terbaca overbuilt~~ ✅ sebagian — aturannya sudah
   tertulis di `ROADMAP.md`, `CARA-KERJA-TIM.md`, dan `BACKLOG.md`; sisanya baru
   terjadi saat proposal & video benar-benar ditulis

### Menurunkan peluang
- Bangun fitur baru di luar alur inti
- Deploy cloud (tidak wajib)
- Fine-tune CLIP (opsional)
- Poles UI lagi

---

## 6. RENCANA 28 HARI (pengganti ROADMAP.md)

### Minggu 1 (28 Jul – 3 Agu)
- [ ] **HARI INI**: verifikasi pendaftaran, ukuran tim, Discord ← **satu-satunya
      yang belum jalan dan memblokir semuanya**
- [x] Push PR #19 → CI hijau → merge (`514f7bb`)
- [x] `docker-compose.yml` + `Dockerfile` + README setup
- [x] Backlog B ke PANDUAN-DATASET
- [ ] **Mulai kumpul foto rak** — bottleneck, bukan koding
- [x] Rapikan angka test di docs

### Minggu 2 (4–10 Agu)
- [ ] Pre-train SKU-110K → fine-tune dataset sendiri → `stoklens-yolo.pt`
- [ ] Labeling Roboflow paralel
- [ ] Catat baseline vs sesudah
- [ ] **Draft proposal mulai sekarang**

### Minggu 3 (11–17 Agu)
- [ ] **Uji lapangan**: enroll 10–20 barang, scan, banding vs manual
- [ ] Tabel akurasi + kurva training
- [ ] Tuning parameter
- [ ] Proposal draft lengkap; skrip kedua video

### Minggu 4 (18–24 Agu)
- [ ] Rekam video proof of work (≤7 mnt, double screen + timestamp, **tanpa cut**)
- [ ] Rekam video promosi (≤5 mnt)
- [ ] Upload YouTube, format judul persis
- [ ] Proposal PDF ≤20 hal, cek plagiarisme, **hapus jejak institusi**
- [ ] **Submit 23 Agustus**

### 25 Agu
- [ ] Submit ulang bila ada perbaikan
- [ ] **Stop commit sebelum 23.55 WIB**

### 9–10 Sep, 20.00
- [ ] Standby Discord, siap live demo

---

## 7. SUMBER

- `[AIC] AI Innovation Challenge.pdf` — rulebook resmi COMPFEST 18, 28 halaman
- Repo `marshal-rizky/Stocklens` @ `612e85f`
- [BINUS Juara 3 CompFest#17 AIC](https://binus.ac.id/bandung/computer-science/2025/09/30/computer-science-binus-juara-3-di-compfest17-ai-innovation-challenge/)
- [Mahasiswa SoCS BINUS di COMPFEST UI 2025](https://socs.binus.ac.id/2025/12/01/mahasiswa-school-of-computer-science-tuai-banyak-prestasi-di-compfest-ui-2025/)
- [AI Innovation Challenge — COMPFEST 18](https://compfest.id/competition/aic)
- [WarungVision](https://warungvision.ddns.net/)
- [Warung Bakso — AuliaSoft](https://www.auliasoft.com/produk/warung-bakso)
- [12 Aplikasi Stock Opname Terbaik — Mekari Desty](https://desty.mekari.com/blog/rekomendasi-aplikasi-stock-opname)
