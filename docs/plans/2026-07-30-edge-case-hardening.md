# Edge Case Hardening — Implementation Plan

> Dibuat 2026-07-30 dari deep review edge case pengguna. Semua temuan di bawah
> **diverifikasi dengan test yang dijalankan**, bukan dugaan dari membaca kode.
> Pola tiap unit: tulis test (RED) → implement (GREEN) → commit.
>
> **Ini BUKAN fitur baru.** Seluruh perubahan memperbaiki kebenaran alur inti
> (enroll → scan → laporan selisih) yang sudah diklaim. Tidak ada penambahan
> ruang lingkup, jadi tidak menambah kesan *overbuilt*.

## Ringkasan temuan & keputusan

| # | Temuan | Tingkat | Keputusan |
|---|---|---|---|
| 1 | Barang tak terdeteksi hilang dari laporan; stoknya tak pernah dikoreksi | 🔴 dire | Section terpisah, **tanpa** auto-shrinkage |
| 2 | Seluruh server beku selama scan/enrollment (event loop diblokir) | 🔴 dire | Pindahkan kerja berat ke threadpool |
| 3 | `qty_fisik` negatif lolos → stok ledger negatif | 🟠 | Validasi `ge=0` |
| 4 | `harga_modal` / `qty_awal` negatif diterima | 🟠 | Validasi `ge=0` |
| 5 | Enrollment tanpa foto → 500 | 🟠 | 400 dengan pesan |
| 6 | Enrollment file bukan gambar → 500 | 🟠 | 400, samakan dengan scan-foto |
| 7 | Ganti nama ke nama duplikat → 500 | 🟠 | 400 dengan pesan |
| 8 | Kode batch dibaca sebagai tanggal expired | 🟠 | Perketat parser |
| 9 | Tanggal scan tersimpan UTC → opname pagi tampil tanggal kemarin | 🟠 | Simpan waktu lokal |

Ditunda (minor, tidak dikerjakan di plan ini): opname-manual menerima
`product_id` tak dikenal / `items` kosong / `product_id` dobel • tidak ada batas
jumlah foto • koneksi SQLite tidak pernah ditutup.

---

## Unit 1 — Kerja berat keluar dari event loop (#2)

**Files:** `stoklens/api.py`, `tests/test_api_concurrency.py` (baru)

### Bukti masalah
Tiga endpoint ditulis `async def` tapi memanggil pipeline sinkron di dalamnya
(`api.py` enrollment, video, foto). Kerja CPU berat jalan **di atas event loop**.
Terukur dengan dua request bersamaan (scan tiruan 3 detik):

```
scan-foto selesai di 3.01 dtk
GET /api/products: mulai 3.31  selesai 3.33 dtk
```

GET tidak bisa **mulai** sampai detik 3,31 — seluruh aplikasi mati selama scan.
Scan foto nyata ±30 detik, dengan OCR bisa menit.

### Test dulu
`tests/test_api_concurrency.py`: httpx `ASGITransport` + `asyncio.gather`, satu
POST scan-foto dengan `scan_photos` di-monkeypatch jadi `time.sleep(0.6)`, dan
satu GET `/api/products` yang dimulai 0,1 detik setelahnya. Assert GET selesai
**sebelum** POST selesai. Ukur waktu ABSOLUT dari satu titik awal — mengukur
durasi GET saja tidak mendeteksi blokade (kesalahan yang sempat kubuat saat
riset).

### Implement
`await run_in_threadpool(kerja)` dari `starlette.concurrency` untuk ketiga
endpoint. **Koneksi SQLite dibuat DI DALAM fungsi thread**, bukan di luar —
`sqlite3.connect` default `check_same_thread=True`, jadi koneksi yang dibuat di
event loop lalu dipakai di thread lain melempar `ProgrammingError`.

Decode gambar (`cv2.imdecode`) juga masuk threadpool — untuk 60 foto itu sendiri
sudah berat. Validasi 400 tetap di dalam thread; `HTTPException` yang dilempar
dari threadpool ditangani normal oleh FastAPI.

Commit: `fix(api): jalankan scan & enrollment di threadpool, jangan blokir event loop`

---

## Unit 2 — Barang tak terdeteksi muncul di laporan (#1)

**Files:** `stoklens/db.py`, `stoklens/api.py`, `stoklens/webui/static/report_view.js`,
`tests/test_db.py`, `tests/test_api_ui.py`, `tests/test_webui.py`

### Bukti masalah
Warung punya Indomie (40 tercatat) dan Yakult (20 tercatat). Scan mendeteksi
Indomie 38, Yakult habis dicuri → 0 deteksi:

```
Baris di laporan : ['Indomie']
total shrinkage  : Rp 6.400        (seharusnya Rp 46.400)
Yakult muncul?    False
Stok Yakult setelah terapkan: 20   (padahal fisiknya 0)
```

Penyebab: `get_report_rows` JOIN ke `scan_items`; barang tanpa deteksi tidak
punya baris. `terapkan_opname` juga hanya menulis ledger untuk item terdeteksi,
jadi stoknya basi selamanya dan kesalahan menumpuk antar-opname.

### Keputusan desain (sudah diputuskan, jangan diubah tanpa alasan)
**Section terpisah, TANPA auto-shrinkage.** Alasannya: kalau barang tak
terdeteksi langsung dianggap fisik 0, maka scan satu rak akan melaporkan seluruh
barang di rak lain sebagai hilang. Menghitungnya otomatis menghasilkan angka
yang salah dengan percaya diri — lebih buruk daripada tidak menghitung.

Konsekuensi yang diterima: user harus menegaskan sendiri mana yang benar-benar
habis (lewat penyesuaian stok yang sudah ada). Stok barang tak terdeteksi tetap
tidak berubah saat "Terapkan" — itu **disengaja**, bukan bug.

### Implement
1. `db.get_tidak_terdeteksi(con, scan_id)` → produk dengan `qty_tercatat > 0`
   yang **tidak** punya baris `scan_items` di scan itu. Return
   `[{id, nama, harga_modal, qty_tercatat, nilai_rp}]` urut nama.
2. `report.build_report(rows, tidak_terdeteksi=())` — parameter opsional, murni,
   additive. Menambah key `tidak_terdeteksi` dan `total_tidak_terdeteksi_rp`.
   **`total_shrinkage_rp` TIDAK berubah** — itu inti keputusannya.
3. Endpoint yang mengembalikan report ikut mengisinya: `/report/{scan_id}`,
   `/api/scans-foto`, `/api/opname-manual`. **`/api/scans` dan `/api/dashboard`
   TIDAK** — keduanya hanya memakai total, dan menambah query per-scan di situ
   mengembalikan N+1 yang baru saja dihapus di PR #32.
4. `report_view.js`: section **"Tidak terdeteksi — perlu dicek"**, hanya tampil
   kalau tidak kosong. Tiap baris: nama, qty tercatat, nilai Rp. Ada kalimat
   penjelas bahwa angkanya belum masuk shrinkage dan perlu dikonfirmasi user.
   Ikut pola yang ada: `escapeHtml()`, `rp()`, ikon Lucide inline, tanpa emoji.

Commit: `feat(report): tampilkan barang tak terdeteksi tanpa menghitungnya sebagai shrinkage`

---

## Unit 3 — Validasi input (#3, #4, #5, #6, #7)

**Files:** `stoklens/api.py`, `tests/test_api.py`, `tests/test_api_ui.py`

### Bukti masalah (semua terverifikasi)
| Aksi | Sekarang | Harusnya |
|---|---|---|
| `qty_fisik: -50` di opname manual | 200, stok ledger jadi −50 | 422 |
| `harga_modal: -5000` saat enrollment | 200, harga jadi −5000 | 422 |
| `qty_awal: -10` saat enrollment | 200, stok jadi −10 | 422 |
| Enrollment tanpa foto | **500** | 400 |
| Enrollment file bukan gambar | **500** | 400 |
| PATCH nama ke nama yang sudah dipakai | **500** | 400 |

Catatan konsistensi: `/api/adjustments` **sudah** menjaga stok negatif lewat
`accounting.apply_adjustment`, dan `/api/scans-foto` **sudah** memvalidasi file
bukan gambar jadi 400. Dua jalur lain tidak. Yang diperbaiki di sini adalah
ketidakkonsistenannya.

### Implement
- Pydantic `Field(ge=0)`: `OpnameItem.qty_fisik`, `ProductPatch.harga_modal` /
  `harga_jual` / `stok_minimum`, `UnknownProdukBaru.harga_modal` / `harga_jual` /
  `stok_minimum` / `qty_awal`.
- Enrollment pakai `Form(..., ge=0)` untuk `harga_modal`, `qty_awal`,
  `harga_jual`, `stok_minimum`.
- `if not fotos: raise HTTPException(400, "Minimal satu foto diperlukan")`.
- Validasi tiap foto bisa dibuka; yang gagal → 400 menyebut nama filenya, pola
  sama dengan `/api/scans-foto`.
- Tangkap `sqlite3.IntegrityError` di `api_product_patch` → 400 "Nama produk
  '…' sudah dipakai", pesan sama dengan yang sudah ada di `/api/unknown/
  {crop_id}/produk-baru`.

Commit: `fix(api): validasi angka negatif, foto kosong, file rusak, dan nama duplikat`

---

## Unit 4 — Parser expired berhenti membaca kode batch (#8)

**Files:** `stoklens/expiry.py`, `tests/test_expiry.py`

### Bukti masalah
```
'LOT 12 05 23 PROD'           -> 2023-05-12   ← kode batch, dianggap expired
'NETTO 85 g  KODE 10 04 22'   -> 2022-04-10   ← kode produksi
'5 2050'                      -> 2050-05-01   ← angka acak
```

Parser mencari pola angka di **seluruh** teks kalau kata kunci tidak ketemu.
Akibatnya user bisa melihat "Potensi rugi expired Rp 240.000" yang seluruhnya
fabrikasi dari kode produksi — angka salah yang ditampilkan dengan percaya diri.

### Implement
Dua aturan tambahan:

1. **Pola angka polos (`DD MM YY`, `MM YY`) hanya diterima kalau ada kata kunci**
   (`EXP`, `ED`, `BB`, `BAIK SEBELUM`, `BEST BEFORE`). Pola dengan nama bulan
   huruf (`AGU 27`) tetap diterima tanpa kata kunci — huruf bulan adalah sinyal
   kuat yang tidak muncul di kode batch.
2. **Tolak tanggal di luar jendela wajar**: lebih tua dari 2 tahun lalu, atau
   lebih dari 10 tahun ke depan. Barang yang kedaluwarsa 3 tahun lalu dalam
   jumlah banyak jauh lebih mungkin salah-baca daripada nyata.

Parameter `hari_ini=None` ditambahkan supaya jendela itu bisa dites tanpa
bergantung tanggal mesin.

Yang HARUS tetap jalan (regresi): `EXP 12 05 2027`, `BB 08 26`,
`BEST BEFORE AGU 27`, `ED: 01/12/2026`.

Commit: `fix(expiry): jangan baca kode batch sebagai tanggal kedaluwarsa`

---

## Unit 5 — Tanggal pakai waktu lokal (#9)

**Files:** `stoklens/db.py`, `docker-compose.yml`, `tests/test_db.py`

### Bukti masalah
```
tersimpan : 2026-07-30 12:10:36   (UTC)
lokal WIB : 2026-07-30 19:10:36
```

Beda 7 jam. Opname antara 00:00–07:00 WIB tampil **bertanggal hari sebelumnya**
di daftar laporan dan kartu stok.

### Implement
Timestamp dihitung di **Python**, bukan mengandalkan `DEFAULT (datetime('now'))`
di SQL. Alasannya penting: default itu ada di `CREATE TABLE`, dan schema dipasang
dengan `IF NOT EXISTS` — mengubah default **tidak berlaku untuk DB yang sudah
ada**, jadi mengubahnya saja akan menghasilkan perilaku berbeda antara DB lama
dan baru.

- Helper `db._sekarang()` → `'YYYY-MM-DD HH:MM:SS'` waktu lokal. Format
  dipertahankan identik supaya konsumen lama tidak pecah.
- Dipakai eksplisit di `add_scan` (`tanggal`), `set_stock` (`tanggal_update`),
  dan `terapkan_opname` (`terapkan_pada`).
- `TZ: Asia/Jakarta` ditambahkan ke `docker-compose.yml` — tanpa itu waktu lokal
  di dalam container tetap UTC.

Baris lama tetap UTC dan tidak dimigrasikan: nilainya cuma tampilan, dan menulis
ulang timestamp riwayat lebih berisiko daripada manfaatnya.

Commit: `fix(db): catat tanggal dalam waktu lokal, bukan UTC`

---

## Definisi selesai

- [ ] Seluruh test hijau (`pytest`), tidak ada test lama yang pecah
- [ ] CI hijau, termasuk workflow Docker (Unit 5 menyentuh compose)
- [ ] Tiap unit punya test yang GAGAL sebelum perbaikannya
- [ ] `BACKLOG.md` diperbarui: temuan minor yang ditunda dicatat
- [ ] Satu PR, commit terpisah per unit
