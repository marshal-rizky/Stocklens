# Plan — Backlog edge case #8–#12 (1 Agustus 2026)

Menutup lima temuan yang sengaja ditunda pada deep review 30 Juli
(`docs/BACKLOG.md` §"Edge case yang sengaja ditunda").

Semua klaim di bawah **diverifikasi ulang terhadap kode pasca-PR #33** sebelum plan
ini ditulis — bukan disalin dari catatan lama. Bukti tiap temuan ada di unitnya.

## Prinsip

- **Tolak, jangan diam-diam perbaiki.** Untuk input yang tidak masuk akal, API
  mengembalikan 400 dengan pesan yang menyebut apa yang salah. Menebak maksud user
  (mis. menggabungkan qty dobel) menyembunyikan bug di sisi pemanggil.
- Pesan galat berbahasa Indonesia, konsisten dengan endpoint lain.
- TDD: test RED dulu yang mereproduksi bug, baru perbaikan.

---

## Unit 1 — Validasi `POST /api/opname-manual` (#8, #9, #10)

Ketiganya cacat validasi pada **satu fungsi yang sama** (`api_opname_manual`), jadi
dikerjakan sekaligus supaya tidak ada tiga suntingan yang saling menimpa.

### Bukti (dijalankan 1 Agustus terhadap `main` @ fd21694)

```
#8  items=[{product_id: 9999, qty_fisik: 5}]     -> 200, laporan berisi 0 item
#9  items=[], terapkan=true                      -> 200, diterapkan=true, scan_id=2
#10 items=[{id:1,qty:3},{id:1,qty:7}], terapkan  -> 200, laporan 2 baris untuk
                                                    produk yang sama (selisih -7 DAN -3),
                                                    3 baris ledger, stok akhir 7
```

`#10` paling parah: karena kedua baris masuk laporan, `total_shrinkage_rp`
**menghitung ganda** — user melihat angka rupiah kerugian yang salah.

### Yang dibangun

Di `api_opname_manual`, sebelum `db.add_scan`:

1. `items` kosong → `400 "Opname harus berisi minimal satu barang"`
2. `product_id` dobel → `400 "product_id dobel dalam satu opname: {daftar}"`
3. `product_id` tidak ada di tabel `products` → `400 "product_id tidak dikenal: {daftar}"`

Urutan dicek sesuai nomor di atas. Daftar id diurutkan supaya pesan deterministik.

### Batas

- Jangan ubah `/api/opname/{scan_id}/terapkan` — guard-nya sudah benar.
- Jangan ubah UI. Checklist di UI memang tidak bisa menghasilkan dobel; yang
  ditutup di sini adalah jalur API langsung.
- Jangan menggabungkan qty yang dobel. Lihat prinsip di atas.

### Verifikasi

- Test RED untuk ketiga kasus, masing-masing memeriksa status 400 **dan** isi pesan.
- Test bahwa opname manual yang sah tetap 200 (regresi).
- Test bahwa tidak ada baris `scans` yang terbuat saat request ditolak.

---

## Unit 2 — Batas jumlah & ukuran foto di `POST /api/scans-foto` (#11)

### Bukti

60 foto diterima, `200`. Tidak ada batas jumlah maupun ukuran di kode.

Bahayanya di RAM, bukan di disk: `cv2.imdecode` menghasilkan array BGR tak
terkompresi. Foto 12 MP → `4032 × 3024 × 3` ≈ **36 MB per gambar**, dan seluruhnya
ditahan bersamaan karena `scan_photos` butuh semua foto untuk dedup antar-foto.
60 foto ≈ 2,1 GB — cukup untuk meng-OOM laptop demo.

### Yang dibangun

Dua konstanta modul di `stoklens/api.py`, dicek **sebelum** decode:

```python
MAKS_FOTO_PER_SCAN = 20
MAKS_BYTE_PER_FOTO = 15 * 1024 * 1024   # 15 MB
```

- jumlah > 20 → `400 "Maksimal 20 foto per scan, dikirim {n}"`
- ada file > 15 MB → `400 "Foto {nama} terlalu besar ({x} MB), maksimal 15 MB"`

**Asumsi angkanya** (dinyatakan supaya bisa dibantah, bukan diam-diam):
20 foto sudah jauh di atas kebutuhan nyata — satu rak biasanya 3–10 foto — dan
menahan batas RAM di ±720 MB. 15 MB melewatkan JPEG 12 MP HP (±5 MB) dengan
kelonggaran besar, tapi menahan file raksasa satuan.

### Batas

- Jangan menambah batas ketiga (total byte). Dua batas sudah menutup kasusnya;
  batas ketiga menambah kerumitan tanpa kasus nyata.
- Jangan mengubah `scan_photos`, `/products`, atau alur enrollment.

### Verifikasi

- Test RED: 21 foto → 400, dan 20 foto → tetap lolos (batasnya inklusif).
- Test RED: satu file > 15 MB → 400 menyebut nama file-nya.
- Cek bahwa validasi terjadi sebelum decode (request besar ditolak murah).

---

## Unit 3 — Tutup koneksi SQLite (#12)

### Bukti

`grep -c "\.close()" stoklens/api.py` → `0`. Setiap endpoint memanggil `con()` lalu
mengandalkan garbage collector.

### ⚠️ KOREKSI — rencana di bawah SALAH, jangan diikuti

> Ditulis ulang 1 Agustus setelah implementasi. **Pendekatan `Depends` di bawah
> tidak boleh dipakai.** Dicoba lebih dulu dan tampak berhasil — 201 test hijau,
> 26 mutan mati — lalu ketahuan pecah total di request bersamaan:
>
> ```
> sqlite3.ProgrammingError: SQLite objects created in a thread can only be used
> in that same thread.
> ```
>
> Endpoint di repo ini `def` (sinkron). FastAPI menjalankan dependency sinkron di
> worker threadpool lewat `contextmanager_in_threadpool`, lalu menjalankan
> handler lewat panggilan `run_in_threadpool` **terpisah** — tidak dijamin worker
> yang sama. Dengan `check_same_thread=True` (yang memang tidak boleh diubah),
> koneksi lahir di satu thread dan dipakai di thread lain.
>
> Tidak terlihat karena `TestClient` mengirim satu request pada satu waktu dan
> anyio memakai ulang worker idle yang sama. Diverifikasi terpisah dengan app
> FastAPI minimal tanpa kode StokLens: berurutan → 200; **20 bersamaan → 20/20
> `ProgrammingError`**.
>
> **Yang benar-benar dibangun:** `contextlib.closing` di **semua 16 titik**,
> seragam, termasuk tiga endpoint berat. Seluruh badan handler sinkron berjalan
> di satu thread threadpool, jadi koneksi lahir, dipakai, dan ditutup di sana.
> Dijaga `tests/test_api_koneksi.py::test_koneksi_aman_saat_request_bersamaan`.
>
> Peta di bawah juga meleset: **16 titik, bukan 15**. Baris `run_scan(con(), ...)`
> inline terlewat, dan `/report` salah diklasifikasikan sebagai threadpool.

### Yang dibangun (RENCANA AWAL — DIBATALKAN, lihat koreksi di atas)

Ubah `con()` menjadi dependency FastAPI yang menutup koneksi setelah response:

```python
def get_con():
    c = db.connect(db_path)
    try:
        yield c
    finally:
        c.close()
```

lalu tiap endpoint `def f(...)` yang tadinya memanggil `c = con()` menjadi
`def f(..., c: sqlite3.Connection = Depends(get_con))`.

**Kecuali tiga endpoint berat** (enrollment, scan video, scan foto): koneksinya
dibuat di dalam fungsi threadpool dan **harus tetap begitu** —
`sqlite3.connect` default `check_same_thread=True`, jadi koneksi milik event loop
akan melempar `ProgrammingError` kalau dipakai di thread lain. Di sana pakai
`contextlib.closing` di dalam fungsi thread-nya.

### Batas

- Perubahan ini menyentuh banyak endpoint. **Hanya ganti cara koneksi diperoleh
  dan ditutup** — jangan ubah logika, nama variabel lain, atau urutan operasi.
- Jangan ubah `db.connect()` sendiri. `isolation_level=""` di sana disandari
  atomicity `terapkan_opname`.
- Kalau jumlah endpoint membuat diff terlalu besar untuk ditinjau aman,
  hentikan dan laporkan — jangan diteruskan setengah jalan.

### Verifikasi

- Seluruh 179 test existing tetap hijau (ini terutama uji regresi).
- Test baru: setelah sejumlah request, tidak ada koneksi menggantung. Diukur
  lewat penghitung pada `sqlite3.Connection` subclass yang disuntik lewat
  parameter `factory` yang sudah disediakan `db.connect()`.

---

## Selesai kalau

- [ ] `pytest -q` hijau seluruhnya
- [ ] Tiap unit punya test RED yang terbukti gagal sebelum perbaikan
- [ ] Tidak ada perubahan di luar `stoklens/api.py`, `tests/`, dan `docs/BACKLOG.md`
- [ ] `docs/BACKLOG.md` §"Edge case yang sengaja ditunda" ditandai selesai
