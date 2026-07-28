# Roadmap StokLens — 28 Juli s/d 25 Agustus 2026

> **DIREVISI TOTAL 2026-07-28** setelah membaca rulebook resmi
> `[AIC] AI Innovation Challenge.pdf`. Versi sebelumnya (disepakati 2026-07-14)
> memakai asumsi deadline "±September 2026" dan menjadwalkan submission di
> minggu 1–7 September — **7–13 hari SETELAH deadline sebenarnya.**
>
> **DEADLINE PENYISIHAN: 25 Agustus 2026, pukul 23.55 WIB.**
> Sisa waktu per 28 Juli: **28 hari.**
>
> Prinsip lama tetap berlaku: **dua jalur paralel** — jalur koding dan jalur
> lapangan (foto, izin toko, labeling). Koding tidak boleh menunggu lapangan.
> Prinsip baru: **kode hanya 25% nilai.** Video + proposal + kesiapan MVP = 45%.

## Verifikasi dulu (BLOKIR — cek hari ini)

Tanpa ini, semua jadwal di bawah tidak ada artinya.

- [ ] Tim sudah terdaftar & berstatus **TIM TERVERIFIKASI**? (Batch 2 tutup 18 Juli)
- [ ] Anggota **3–5 orang** WNI, usia ≤25, pelajar/mahasiswa aktif hingga 27 Sep 2026?
- [ ] Hadir AIC Talks 25 Juli + isi presensi? (bonus 1.5%)
- [ ] Dapat VPS/GPU credits gratis (30 pendaftar pertama)?
- [ ] Semua anggota di Discord AIC, nickname `[Nama Tim] - [Nama]`?

## Deliverable penyisihan (4 item, bukan 3)

| # | Deliverable | Spesifikasi | Status |
|---|---|---|---|
| 1 | Repo GitHub **public** | README setup guide + **docker compose** | ✅ Terverifikasi otomatis tiap PR lewat workflow `Docker` — build image, container merespons, endpoint inti benar, DB tertulis ke volume host. Ukuran image 2,19 GB, build ±1,5 menit di runner |
| 2 | Video **proof of work** | ≤7 mnt, YouTube **unlisted**, `COMPFEST 18 AIC: PROOF OF WORK - [Tim] - [Proyek]` | ❌ |
| 3 | Video **promosi inovasi** | ≤5 mnt, YouTube **public**, MP4 ≥720p, `COMPFEST 18 AIC: [Tim] - [Proyek]` | ❌ |
| 4 | **Proposal PDF** | ≤20 hal di luar cover/pustaka/lampiran | ❌ |

Boleh submit berkali-kali; **yang dinilai submisi terakhir**. Tidak submit =
dianggap mengundurkan diri.

## Timeline

| Minggu | Jalur koding / dokumen | Jalur lapangan (paralel) |
|---|---|---|
| **1** (28 Jul–3 Agu) | ~~merge PR #19~~ ✅ • ~~`docker-compose.yml` + `Dockerfile` + README setup~~ ✅ • ~~Backlog B: aturan kondisi foto~~ ✅ • ~~rapikan angka test di docs~~ ✅ • **sisa: verifikasi pendaftaran** | **Izin toko + mulai kumpul foto rak** (target ≥500). Ini bottleneck utama — jangan tunda |
| **2** (4–10 Agu) | **Fine-tune YOLO** (WAJIB rulebook): pre-train SKU-110K → fine-tune dataset sendiri → tukar model. Lihat `PANDUAN-FINETUNE.md` • **mulai draft proposal sekarang**, jangan tunggu model | Labeling Roboflow + QC |
| **3** (11–17 Agu) | Tuning threshold/parameter dari hasil uji • proposal draft lengkap • tulis skrip kedua video | **Uji lapangan**: enroll 10–20 barang, scan, bandingkan vs hitung manual. Catat tabel akurasi |
| **4** (18–24 Agu) | **Rekam & edit 2 video** • finalisasi proposal PDF • cek plagiarisme • **hapus semua jejak institusi** • **submit 23 Agu** | Testimoni/feedback toko pilot untuk video |
| **25 Agu** | Submit ulang bila ada perbaikan • **stop commit sebelum 23.55 WIB** | — |
| **9–10 Sep, 20.00** | **Standby Discord** — panitia bisa minta live demo, wajib jawab ≤2 jam | — |

## Scope penyisihan — BATAS KERAS DARI RULEBOOK

Rulebook membatasi ruang lingkup MVP dengan huruf tebal: **WAJIB HANYA SAMPAI**
alur interaksi inti. Kriteria penilaian bertanya eksplisit *"tidak **overbuilt**
atau underbuilt?"*

**Alur inti = enroll → scan → laporan selisih.** Itu saja yang jadi bintang.

**Wajib ada:** model fine-tuned sendiri (+bukti kurva training & tabel baseline
vs sesudah) • angka uji lapangan nyata • mode foto sebagai demo utama (paling
stabil) • docker compose.

**JANGAN bangun lagi** (menambah kesan overbuilt):
- Export CSV per-laporan (eks-backlog #3) — **dibatalkan**
- Fitur dashboard/analitik baru
- Deployment cloud — **tidak wajib**, babak final cukup localhost
- Fine-tune CLIP — opsional, YOLO sudah memenuhi syarat rulebook
- Poles UI lagi

**Fitur yang sudah terlanjur dibangun di luar alur inti** (Beranda KPI, riwayat
opname, export CSV, ledger, opname manual) **tidak dihapus**, tapi:
- Di proposal & video, diposisikan sebagai *pendukung*, bukan fitur utama
- Di video proof of work, demokan alur inti dulu dan paling lama
- Siapkan jawaban untuk juri: *"Ledger diperlukan karena selisih stok tidak
  bermakna tanpa angka tercatat sebagai pembanding — itu bagian dari output
  core inference, bukan analitik tambahan."*

**Ditunda pasca-penyisihan:** TWA/Play Store • on-device inference • stitching
antar-foto • multi-user auth • integrasi POS.

## Bobot penilaian (dari rulebook)

| Kriteria | Bobot |
|---|---|
| Implementasi Teknologi & Kematangan Arsitektur | 25% |
| Orisinalitas dan Dampak Sosial | 20% |
| Kesiapan MVP untuk Babak Final | 15% |
| Video Promosi | 15% |
| Kualitas Proposal & Proses Pengembangan | 15% |
| Relevansi dengan Tema | 10% |
| Business Value & Governance (BONUS) | 3.5% |
| AIC Talks (BONUS) | 1.5% |

Konsekuensi: **jangan habiskan 90% waktu di 25% nilai.** Video dan proposal
punya bobot gabungan 30% dan belum dikerjakan sama sekali.

## Risiko utama

1. **Deadline salah di roadmap lama** → sudah diperbaiki dokumen ini. Sisa 28
   hari, bukan 8–10 minggu.
2. **45% bobot ada di deliverable yang belum disentuh** (video promosi, proposal,
   kesiapan MVP) → mulai proposal minggu 2, jangan tunggu model selesai.
3. **Izin toko & labeling molor** → tetap bottleneck nomor satu. Mulai minggu ini.
4. **Terbaca overbuilt** → bingkai ulang scope di proposal & video (lihat atas).
5. Akurasi model zero-shot kurang di lapangan → guided mode + tuning threshold
   adalah jaring pengaman; fine-tune memperbaiki sisanya.
6. **Video proof of work DILARANG di-cut** — hanya fast-forward + voice over,
   wajib double screen (terminal + aplikasi) plus timestamp. Salah rekam =
   ulang dari nol. Sisakan waktu.

## Status fondasi (sudah selesai, merged di main)

Pipeline video (YOLO+BoT-SORT+ReID+line-crossing) • Photo mode • Enrollment
few-shot CLIP • Enroll dari hasil scan • OCR expired Indonesia • Akuntansi
(ledger, adjustment, opname manual, KPI, export CSV) • JSON API lengkap •
UI mobile web • CI GitHub Actions • **docker compose** • suite test hijau
(cek jumlahnya dengan `pytest -q --collect-only`, jangan disalin ke docs).

## Dokumen terkait

- `AUDIT-RULEBOOK-2026-07-28.md` — audit lengkap terhadap rulebook, rincian
  penilaian, dan estimasi peluang
- `../STATUS.md` — papan status mingguan (PIC, progres, blocker)
- `CARA-KERJA-TIM.md` — aturan kerja tim 3–5 orang
- `PANDUAN-DATASET.md` — SOP foto & labeling
- `PANDUAN-FINETUNE.md` — alur fine-tune YOLO
- `CATATAN-TIM.md` — peta modul & keputusan desain
