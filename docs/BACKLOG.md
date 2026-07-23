# Backlog StokLens

> Daftar perbaikan yang DISENGAJA ditunda. Ambil satu, bikin branch `fitur/...` atau
> `fix/...`, kerjakan, PR. Jangan dikerjakan diam-diam tanpa klaim di grup.
> Update terakhir: 2026-07-18 (tambah bagian Akurasi pengenalan — prioritas tertinggi).

## Selesai (branch `fitur/ui-beranda-redesign`, menunggu merge)

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

**B. Perbarui `PANDUAN-DATASET.md` dengan aturan kondisi foto.**
- Dataset detektor: WAJIB foto rak asli (kayu/kaca/besi, padat/setengah kosong).
  Foto barang di meja hampir tidak berguna; foto stock internet MERUSAK (bias ke
  latar putih yang tak pernah ada di gudang).
- Enrollment: potret di kondisi yang sama dengan saat scan — jarak mirip, cahaya toko
  yang sama, 3–5 sudut. Jangan pakai foto stock/marketplace.
- Rak kaca perlu sampel ekstra (pantulan & barang tembus pandang lebih sulit).

**C. Auto-labeling untuk hemat waktu tim.**
Pakai model hasil pre-train SKU-110K untuk melabeli otomatis foto rak kita, tim tinggal
MENGOREKSI di Roboflow, bukan menggambar dari nol. Estimasi: 20–40 jam-orang → 3–5 jam.

*Catatan riset (18 Jul):* dataset produk Indonesia publik praktis TIDAK ADA yang layak
— Roboflow `rak-minimarket` 53 gambar, `dataset-rak-minimarket` 26 gambar, sisanya
proyek capstone 200–400 gambar foto produk tunggal. Scraping marketplace ditolak:
melanggar ToS + hak cipta (risiko diskualifikasi rulebook #17) DAN salah jenis data
(foto katalog latar putih, bukan adegan rak). Andalan tetap SKU-110K + 200–500 foto
rak sendiri.

## Teknis (temuan final review branch UI, belum dikerjakan)

3. Export CSV **per-laporan opname** (sekarang hanya buku stok global) — juri/user
   yang buka satu laporan mungkin berharap bisa unduh laporan itu saja.
4. Konsolidasi dua jalur terapkan-ke-ledger (`/api/opname-manual` inline vs
   `/api/opname/{id}/terapkan`) jadi satu helper bersama + transaksi atomik.
5. ✅ **SELESAI** (commit `7b3e1d7`, branch `fix/api-status-code`) — `api()` di `app.js`
   belum meng-expose status code — `barang_detail.js` dan `report_view.js` terpaksa
   pakai raw fetch untuk bedakan 404/409. Tambah opsi di `api()` lalu hapus duplikasi.
6. ✅ **SELESAI** (commit `81150d8`, branch `fix/report-404-scan-tak-ada`) — `GET
   /report/{scan_id}` mengembalikan `scan: null` untuk id tak dikenal, tidak
   konsisten dengan endpoint /api/* lain yang 404.
7. `GET /api/scans` & `/api/dashboard` menghitung `build_report` per scan per request
   (N+1) — aman untuk prototype, perbaiki kalau riwayat sudah ratusan.

## Keterbatasan yang diterima (known limitations)

- Harga jual tidak bisa dikosongkan kembali setelah diisi (PATCH membuang null) —
  komentar penjelas ada di `barang_detail.js`.
- Mode `line` menghasilkan hitungan 0 untuk kamera statis — by design, pakai `track`.
- Ketik di kolom cari saat state error di halaman Barang menampilkan pesan kosong
  yang salah (kasus pojok kosmetik).
