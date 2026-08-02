# Papan Status StokLens

> Diperbarui tiap **sync mingguan (Minggu malam)** — lihat `docs/CARA-KERJA-TIM.md` §6.
> Kenapa file dan bukan chat grup: chat hilang, file bisa dibaca orang yang baru gabung.
>
> **Deadline penyisihan: 25 Agustus 2026, 23.55 WIB.**
> Update terakhir: 2026-07-28.

## Cara pakai

1. Kolom **PIC** wajib berisi nama. Kosong = pekerjaan itu tidak terjadi.
2. Kolom **Status**: `belum` / `jalan (x/y)` / `selesai` / `terblokir`.
3. Kalau `terblokir`, kolom Blocker wajib diisi — itu bahan bahasan sync.
4. Baris tidak dihapus setelah selesai; itu jejak untuk bab "proses pengembangan"
   di proposal (bobot 15%).

---

## Deliverable penyisihan (4 item wajib)

| # | Deliverable | PIC | Status | Blocker |
|---|---|---|---|---|
| 1 | Repo public + README setup + **docker compose** | | selesai | — terverifikasi otomatis tiap PR lewat workflow `Docker` |
| 2 | Video proof of work (≤7 mnt, unlisted) | | belum | butuh fitur final + uji lapangan |
| 3 | Video promosi (≤5 mnt, public, ≥720p) | | belum | butuh skrip |
| 4 | Proposal PDF (≤20 hal) | | belum | — mulai minggu 2, jangan tunggu model |

Format judul YouTube & aturan "dilarang cut" ada di `docs/ROADMAP.md`. Salah format = gugur.

## Verifikasi administratif (BLOKIR — belum ada yang mengonfirmasi)

| Item | PIC | Status | Blocker |
|---|---|---|---|
| Tim terdaftar & berstatus TIM TERVERIFIKASI | | belum | |
| Anggota 3–5 orang, syarat usia/status pelajar terpenuhi | | belum | |
| Presensi AIC Talks 25 Juli (bonus 1.5%) | | belum | sudah lewat — cek masih terhitung/tidak |
| Semua anggota di Discord AIC, nickname sesuai format | | belum | |
| VPS/GPU credits gratis (30 pendaftar pertama) | | belum | |

## Minggu 1 (28 Jul – 3 Agu)

| Pekerjaan | PIC | Status | Blocker |
|---|---|---|---|
| Merge PR #19 konsolidasi ledger | | selesai | — (`b8b35c2`) |
| `Dockerfile` + `docker-compose.yml` + README setup | | selesai | — |
| Verifikasi docker jalan sungguhan | | selesai | dijawab lewat workflow CI `Docker`, bukan lewat laptop — build + smoke test tiap PR |
| Backlog B: aturan kondisi foto ke `PANDUAN-DATASET.md` | | selesai | — |
| Rapikan angka test & baris stale di docs | | selesai | — |
| **Izin toko** (target 2–3 lokasi) | | belum | **bottleneck utama** |
| **Kumpul foto rak** (target ≥500) | | 0/500 | menunggu izin toko |

## Minggu 2 (4–10 Agu)

| Pekerjaan | PIC | Status | Blocker |
|---|---|---|---|
| Pre-train SKU-110K | | **selesai** | dikerjakan lebih awal 28 Jul — mAP50 0,868, 37 menit di RTX 4070 |
| **Salin bukti training ke Drive tim** | | belum | `best.pt`, `results.png`, `results.csv`, confusion matrix ada di `C:\Users\User\StokLens-training\` — di luar repo & di-gitignore, jadi HILANG kalau laptop ketua bermasalah |
| Fine-tune dataset sendiri → `stoklens-yolo.pt` | | belum | menunggu dataset berlabel |
| **Proyek Roboflow + pipa auto-label** | | **selesai** | `marshal-rizky/stoklens-produk-warung` — 25 foto, 131 kotak, batch `gdino-ronde1` menunggu review |
| Labeling Roboflow + QC | | **bisa mulai** | 25 foto sudah siap dibetulkan; sisanya menunggu foto |
| Catat baseline vs sesudah (Step 0 & 3 PANDUAN-FINETUNE) | | baseline "sebelum" selesai | belum mAP — belum ada label manusia |
| **Draft proposal mulai** | | belum | — jangan tunggu model |

## Minggu 3 (11–17 Agu)

| Pekerjaan | PIC | Status | Blocker |
|---|---|---|---|
| Uji lapangan: enroll 10–20 barang, scan vs hitung manual | | belum | |
| Tabel akurasi + kurva training | | belum | |
| Tuning parameter (tabel di `CATATAN-TIM.md`) | | belum | |
| Proposal draft lengkap | | belum | |
| Skrip kedua video | | belum | |

## Minggu 4 (18–24 Agu)

| Pekerjaan | PIC | Status | Blocker |
|---|---|---|---|
| Rekam video proof of work (tanpa cut, double screen + timestamp) | | belum | |
| Rekam + edit video promosi | | belum | |
| Upload YouTube, cek format judul & visibility | | belum | |
| Proposal PDF final, cek plagiarisme, hapus jejak institusi | | belum | |
| **Submit 23 Agustus** (buffer 2 hari) | | belum | |

## Risiko yang sedang dipantau

| Risiko | Pemantau | Kondisi sekarang |
|---|---|---|
| Izin toko & kumpul foto molor | | **risiko tertinggi.** Auto-labeling memangkas waktu *menggambar*, bukan waktu *memotret* — 135 foto rak tertriase vs target 500 |
| Foto uji bocor ke training | | dijaga di hulu: `scripts/testset.py` + `--daftar-uji`. Kalau bocor, tidak ada yang gagal dan angkanya justru terlihat bagus |
| 45% bobot ada di deliverable yang belum disentuh | | video & proposal masih 0% |
| Terbaca *overbuilt* oleh juri | | mitigasi: BACKLOG dikunci, framing alur inti di proposal |
| Konflik semantik antar-PR | | aturan ada di `CARA-KERJA-TIM.md` §5, belum diuji ulang |
