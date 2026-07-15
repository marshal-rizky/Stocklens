# Backlog StokLens

> Daftar perbaikan yang DISENGAJA ditunda. Ambil satu, bikin branch `fitur/...` atau
> `fix/...`, kerjakan, PR. Jangan dikerjakan diam-diam tanpa klaim di grup.
> Update terakhir: 2026-07-15 (2 item UI selesai — lihat bagian Selesai).

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

## Teknis (temuan final review branch UI, belum dikerjakan)

3. Export CSV **per-laporan opname** (sekarang hanya buku stok global) — juri/user
   yang buka satu laporan mungkin berharap bisa unduh laporan itu saja.
4. Konsolidasi dua jalur terapkan-ke-ledger (`/api/opname-manual` inline vs
   `/api/opname/{id}/terapkan`) jadi satu helper bersama + transaksi atomik.
5. `api()` di `app.js` belum meng-expose status code — `barang_detail.js` dan
   `report_view.js` terpaksa pakai raw fetch untuk bedakan 404/409. Tambah opsi
   di `api()` lalu hapus duplikasi.
6. `GET /report/{scan_id}` mengembalikan `scan: null` untuk id tak dikenal, tidak
   konsisten dengan endpoint /api/* lain yang 404.
7. `GET /api/scans` & `/api/dashboard` menghitung `build_report` per scan per request
   (N+1) — aman untuk prototype, perbaiki kalau riwayat sudah ratusan.

## Keterbatasan yang diterima (known limitations)

- Harga jual tidak bisa dikosongkan kembali setelah diisi (PATCH membuang null) —
  komentar penjelas ada di `barang_detail.js`.
- Mode `line` menghasilkan hitungan 0 untuk kamera statis — by design, pakai `track`.
- Ketik di kolom cari saat state error di halaman Barang menampilkan pesan kosong
  yang salah (kasus pojok kosmetik).
