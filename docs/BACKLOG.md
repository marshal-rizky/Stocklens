# Backlog StokLens

> Daftar perbaikan yang DISENGAJA ditunda. Ambil satu, bikin branch `fitur/...` atau
> `fix/...`, kerjakan, PR. Jangan dikerjakan diam-diam tanpa klaim di grup.
> Update terakhir: 2026-07-15.

## UI improvement (masukan dari uji pakai ketua, 15 Jul)

1. **Beranda: satu scroll vertikal saja.**
   Saat ini kartu KPI di-scroll horizontal (kanan-kiri) — terasa tidak alami.
   Ubah jadi susunan vertikal/stack (atau grid 2 kolom + 1 full-width) supaya seluruh
   beranda cukup di-scroll ke bawah. Sentuh: `app.css` (.kpi-grid), cek juga dampaknya
   di ringkasan `report_view.js` yang memakai kelas yang sama — kemungkinan perlu
   kelas terpisah antara KPI beranda dan totals laporan.

2. **Ambil foto: multi-shot tanpa keluar-masuk kamera.**
   Sekarang `capture="environment"` membuka kamera → jepret 1 → balik ke form → ulangi.
   Harusnya bisa ambil/pilih banyak foto sekaligus. Opsi implementasi (pilih saat
   mengerjakan): (a) hilangkan atribut `capture` supaya muncul picker galeri yang
   mendukung multi-select + tombol kamera bawaan picker; (b) dua tombol: "Ambil Foto"
   (kamera, satu-satu) dan "Pilih dari Galeri" (multi); (c) kamera in-app via
   getUserMedia dengan tombol jepret berulang — paling mulus tapi paling besar
   kerjaannya (dan jadi fondasi fitur overlay panduan SOP di roadmap).
   Berlaku di: `barang_baru.js` (enrollment) dan `opname_foto.js`.

## Teknis (temuan final review branch UI, belum dikerjakan)

3. Export CSV **per-laporan opname** (sekarang hanya buku stok global) — juri/user
   yang buka satu laporan mungkin berharap bisa unduh laporan itu saja.
4. Konsolidasi dua jalur terapkan-ke-ledger (`/api/opname-manual` inline vs
   `/api/opname/{id}/terapkan`) jadi satu helper bersama + transaksi atomik.
5. ✅ **SELESAI** (commit `7b3e1d7`, branch `fix/api-status-code`) — `api()` di `app.js`
   belum meng-expose status code — `barang_detail.js` dan `report_view.js` terpaksa
   pakai raw fetch untuk bedakan 404/409. Tambah opsi di `api()` lalu hapus duplikasi.
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
