# Backlog StokLens

> Daftar perbaikan yang DISENGAJA ditunda. Ambil satu, bikin branch `fitur/...` atau
> `fix/...`, kerjakan, PR. Jangan dikerjakan diam-diam tanpa klaim di grup.
> Update terakhir: 2026-07-28 (sinkron dengan `AUDIT-RULEBOOK-2026-07-28.md`).
>
> ⚠️ **Sejak 28 Juli, backlog ini TIDAK boleh dipakai sebagai daftar kerjaan bebas.**
> Rulebook AIC menghukum MVP yang *overbuilt*, dan alur inti sudah lengkap. Sebelum
> mengambil item mana pun, cek dulu: *"ini bagian dari enroll → scan → laporan
> selisih?"* Kalau bukan → jangan dikerjakan sampai penyisihan lewat. Prioritas 28
> hari ke depan ada di `ROADMAP.md`, bukan di sini.

## Selesai (branch `fitur/ui-beranda-redesign`, sudah merged ke main)

1. ~~**Beranda: satu scroll vertikal saja.**~~ ✅ SELESAI.
   KPI horizontal diganti: kartu hero "Nilai stok" full-width + 2 metrik berdampingan
   (grid), tanpa scroll samping. Ditambah baris "Aksi cepat" (Mulai Opname / Tambah
   Barang) dan section "Riwayat opname" (3 scan terakhir) untuk mengisi ruang kosong
   dengan konten berguna. `report_view.js` totals ikut pakai grid wrap (tidak scroll).

2. ~~**Ambil foto: multi-shot tanpa keluar-masuk kamera.**~~ ✅ SELESAI (opsi b).
   Dua tombol di enrollment (`barang_baru`) dan opname foto (`opname_foto`):
   "Ambil Foto" (kamera, `capture`, satu-satu) + "Pilih dari Galeri" (`multiple`, tanpa
   `capture`, banyak sekaligus). Keduanya menambah ke daftar foto yang sama.
   Catatan: kamera in-app via getUserMedia (opsi c) belum — itu fondasi fitur overlay
   panduan SOP di roadmap, dikerjakan nanti kalau perlu.

## Akurasi pengenalan (PRIORITAS TERTINGGI — dari analisis 18 Jul)

**A. Enroll dari hasil scan ("unknown" → beri nama → masuk galeri).** ✅ **SELESAI**
(Unit 1–4, merged via PR #13/#15/#16 — lihat `docs/plans/2026-07-18-enroll-dari-scan.md`).
Dampak terbesar ke akurasi, lebih besar daripada menambah ratusan foto dataset.

> ⚠️ *Catatan implementasi di bawah sudah USANG dan salah satu sarannya SENGAJA
> DITOLAK saat implementasi.* Dipertahankan cuma sebagai jejak analisis. Yang
> benar-benar dibangun: galeri multi-embedding (entri terpisah, matching ambil
> similarity TERTINGGI), **bukan** merata-ratakan embedding. Merata-ratakan foto
> enrollment tampak-depan dengan crop scan menyerong menghasilkan vektor yang
> tidak cocok ke dua-duanya. Endpoint finalnya `POST /api/unknown/{crop_id}/assign`
> dan `.../produk-baru`, bukan `POST /api/products/{id}/tambah-embedding`.
> Jangan bangun ulang dari catatan ini — baca plan doc-nya.

*Masalah:* enrollment sekarang dipotret terpisah (close-up, cahaya beda, sudut lurus),
sedangkan crop hasil scan kecil, agak blur, dan menyerong. Ketidakcocokan kondisi ini
— bukan material rak — adalah penyebab utama gagal-match. Urutan faktor perusak:
(1) beda skala/ketajaman, (2) beda cahaya/suhu warna, (3) beda sudut, (4) latar/rak,
(5) foto stock internet (paling buruk; desain kemasannya sering versi lama).

*Solusi:* hilangkan ketidakcocokan di akarnya. Saat scan menghasilkan item `unknown`,
tampilkan crop-nya di laporan → user tap → pilih produk yang sudah ada ATAU daftarkan
baru → crop itu ditambahkan ke galeri embedding produk tersebut. Kondisinya otomatis
identik dengan kondisi scan, dan galeri makin kaya tiap pemakaian (self-improving).

*Catatan implementasi:* pipeline sudah mendeteksi item unknown (`scan_items.product_id`
NULL) tapi crop-nya belum disimpan. Perlu: simpan crop unknown (file/blob + referensi
di DB), endpoint `POST /api/products/{id}/tambah-embedding` (rata-ratakan embedding
lama dengan yang baru — lihat `matcher.average_embedding`), dan UI di `report_view.js`
untuk menampilkan crop unknown + aksi "Ini barang apa?".

**B. Perbarui `PANDUAN-DATASET.md` dengan aturan kondisi foto.** ✅ **SELESAI**
(2026-07-28) — lihat `PANDUAN-DATASET.md` §"Kondisi foto — aturan keras". Isinya:
aturan terpisah untuk dataset detektor (wajib rak asli; foto meja & foto stock
internet dilarang) vs enrollment (potret di kondisi scan), plus sampel ekstra untuk
rak kaca dan urutan faktor perusak match.

**C. Auto-labeling untuk hemat waktu tim.** ✅ **SIAP DIPAKAI** (2026-07-28) — model
pre-train SKU-110K sudah jadi (mAP50 0,868), dan cara pakainya sudah ditulis di
`PANDUAN-DATASET.md` §"Auto-labeling" lengkap dengan skrip, alasan ambang, dan
daftar hal yang tetap wajib dikoreksi manusia (renceng, etalase kaca, rak remang).
Estimasi tetap: 20–40 jam-orang → 3–5 jam. **Menunggu foto, bukan menunggu kode.**

> **Koreksi 2026-08-01:** ambangnya semula `conf=0.25` — angka yang diambil dari
> nalar, tanpa pernah diuji ke foto warung. Disapu ke 91 foto rak asli: median cuma
> 7 kotak dan 15 foto dapat NOL kotak, jadi janji hemat waktu itu tidak berlaku.
> Sekarang `conf=0.05` (median 46 kotak, tidak ada foto kosong). Tabel sapuannya ada
> di `PANDUAN-DATASET.md`.

*Catatan riset (18 Jul):* dataset produk Indonesia publik praktis TIDAK ADA yang layak
— Roboflow `rak-minimarket` 53 gambar, `dataset-rak-minimarket` 26 gambar, sisanya
proyek capstone 200–400 gambar foto produk tunggal. Scraping marketplace ditolak:
melanggar ToS + hak cipta (risiko diskualifikasi rulebook #17) DAN salah jenis data
(foto katalog latar putih, bukan adegan rak). Andalan tetap SKU-110K + 200–500 foto
rak sendiri.

## Teknis (temuan final review branch UI, belum dikerjakan)

3. ❌ **DIBATALKAN 2026-07-28** — Export CSV **per-laporan opname** (sekarang hanya
   buku stok global). Alasan pembatalan: export sudah di luar alur inti
   (enroll → scan → laporan selisih), dan rulebook menilai *overbuilt* secara negatif
   di kriteria "Kesiapan MVP" (15%). Export CSV global yang sudah ada tidak dihapus,
   tapi jangan ditambah. Boleh ditinjau ulang setelah 25 Agustus.
4. ✅ **SELESAI** (branch `fix/konsolidasi-terapkan-ledger`, seluruh rangkaian
   commit-nya — `c1dfe4f` sendirian belum utuh) — Konsolidasi dua jalur
   terapkan-ke-ledger (`/api/opname-manual` inline vs `/api/opname/{id}/terapkan`)
   jadi satu helper bersama `db.terapkan_opname()` + transaksi atomik. Termasuk:
   guard urutan (report dibangun sebelum terapkan), `isolation_level=""` di-set
   eksplisit di `db.connect()` karena atomicity-nya bersandar ke situ, dan guard
   terapkan-ganda jadi compare-and-set di dalam helper (bukan cek-lalu-tulis
   lintas koneksi yang bisa kalah balapan).
5. ✅ **SELESAI** (commit `b41703c`, branch `fix/api-status-code`) — `api()` di `app.js`
   belum meng-expose status code — `barang_detail.js` dan `report_view.js` terpaksa
   pakai raw fetch untuk bedakan 404/409. Tambah opsi di `api()` lalu hapus duplikasi.
6. ✅ **SELESAI** (commit `5bee344`, branch `fix/report-404-scan-tak-ada`) — `GET
   /report/{scan_id}` mengembalikan `scan: null` untuk id tak dikenal, tidak
   konsisten dengan endpoint /api/* lain yang 404.
7. ✅ **SELESAI** (commit `3c9513f`, branch `fix/n-plus-1-riwayat-opname`) — `GET
   /api/scans` menghitung `build_report` per scan per request (N+1). Tambah
   `db.get_report_rows_by_scan()` (query konstan, dikelompokkan per scan_id di
   Python) dan pakai di endpoint itu; `get_report_rows()` lama tetap dipakai
   enam pemanggil lain, tidak diubah.

   > **Koreksi 2026-07-28:** versi lama item ini ikut menuduh `/api/dashboard` N+1.
   > Salah — endpoint itu memanggil `build_report` **sekali** untuk scan terakhir saja.
   > Yang benar-benar N+1 cuma `/api/scans`. Jangan "memperbaiki" `/api/dashboard`.

## Edge case yang sengaja ditunda (dari deep review 2026-07-30)

Temuan minor dari review edge case pengguna. Yang dire dan penting sudah
dikerjakan — lihat `plans/2026-07-30-edge-case-hardening.md`. Sisanya di bawah
**terverifikasi nyata** tapi dinilai tidak sepadan dikerjakan sebelum 25 Agustus.

8. `POST /api/opname-manual` menerima `product_id` yang tidak ada → 200, lalu
   item itu hilang senyap dari laporan (JOIN membuangnya). User yang mengirim 30
   item dengan satu id salah tidak diberi tahu apa pun.
9. `POST /api/opname-manual` dengan `items: []` → membuat scan kosong dan
   menandainya "sudah diterapkan". Tidak merusak data, cuma bikin daftar laporan
   penuh baris tak berguna.
10. `product_id` dobel dalam satu opname manual → produk yang sama muncul dua
    baris di laporan, dan `terapkan` menulis dua baris ledger (yang terakhir
    menang). UI checklist tidak memungkinkan ini; API langsung memungkinkan.
11. **Tidak ada batas jumlah maupun ukuran foto** di `/api/scans-foto` — 60 foto
    diterima. Foto 12 MP jadi ±36 MB per gambar setelah decode dan semuanya
    ditahan di RAM sekaligus, jadi memilih seluruh galeri bisa membuat laptop
    demo OOM. **Kandidat paling layak diambil** dari daftar ini.
12. Koneksi SQLite tidak pernah ditutup (`0` panggilan `.close()` di `api.py`) —
    mengandalkan GC. Tidak terbukti menyebabkan kegagalan saat diuji terisolasi,
    tapi menyisakan file handle menggantung.

## Keterbatasan yang diterima (known limitations)

- Harga jual tidak bisa dikosongkan kembali setelah diisi (PATCH membuang null) —
  komentar penjelas ada di `barang_detail.js`.
- Mode `line` menghasilkan hitungan 0 untuk kamera statis — by design, pakai `track`.
- Ketik di kolom cari saat state error di halaman Barang menampilkan pesan kosong
  yang salah (kasus pojok kosmetik).
