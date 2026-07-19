# Enroll dari Scan — Implementation Plan

> Branch: `fitur/enroll-dari-scan`. Dikerjakan subagent per unit: implement → spec
> review → quality review → fix loop. Jangan merge sebelum CI hijau.

**Goal:** Item yang tidak dikenali saat scan ("unknown") bisa ditap user → diberi nama →
crop-nya masuk galeri embedding produk. Menghilangkan ketidakcocokan kondisi
(enrollment close-up vs crop scan kecil/menyerong) yang jadi penyebab utama gagal-match.

## Keputusan desain (jangan diubah tanpa alasan kuat)

**1. Galeri multi-embedding, BUKAN rata-rata.**
Merata-ratakan foto enrollment tampak-depan dengan crop scan menyerong menghasilkan
vektor yang tidak cocok ke dua-duanya. Simpan sebagai entri terpisah, matching ambil
**similarity tertinggi** di antara semua entri milik produk itu. Ini juga alasan kenapa
`products.embedding` (rata-rata enrollment) tetap dipertahankan sebagai entri pertama.

**2. Embedding crop disimpan saat scan, bukan dihitung ulang saat assign.**
Konsekuensi bagus: endpoint assign TIDAK perlu memuat CLIP sama sekali (cepat + bisa
dites tanpa torch). Biaya ~2KB per crop.

**3. Crop disimpan sebagai file gambar** di `data/crops/`, path dicatat di DB, disajikan
lewat mount `/crops`. `data/` masuk `.gitignore`.

## Skema DB (tambahan, migrasi aman untuk DB lama)

```sql
CREATE TABLE product_embeddings(          -- referensi tambahan di luar enrollment
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  embedding BLOB NOT NULL,
  sumber TEXT DEFAULT 'scan',
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE unknown_crops(               -- deteksi tak dikenali, menunggu diberi nama
  id INTEGER PRIMARY KEY,
  scan_id INTEGER NOT NULL REFERENCES scans(id),
  crop_path TEXT NOT NULL,
  embedding BLOB NOT NULL,
  product_id INTEGER REFERENCES products(id),   -- NULL = belum di-resolve
  created_at TEXT DEFAULT (datetime('now'))
);
```

---

## Unit 1 — DB galeri + matcher max-similarity

**Files:** `stoklens/db.py`, `stoklens/matcher.py`, `tests/test_db.py`, `tests/test_matcher.py`

Test untuk DB **sudah ditulis** di `tests/test_db.py` (3 test terakhir, sekarang RED).
Implementasikan supaya hijau:
- `add_product_embedding(con, product_id, embedding, sumber="scan")`
- `all_products(con)` → tiap produk dapat key baru **`embeddings`** = `[embedding enrollment] + [entri product_embeddings urut id]`. Key lama `embedding` tetap ada (jangan dihapus, dipakai kode lain).
- `add_unknown_crop(con, scan_id, crop_path, embedding)` → id
- `list_unknown_crops(con, scan_id=None, hanya_belum=True)` → list dict (id, scan_id, crop_path, product_id, created_at); `hanya_belum=True` menyaring `product_id IS NULL`
- `get_unknown_crop(con, crop_id)` → dict termasuk `embedding` (np array), None kalau tidak ada
- `resolve_unknown_crop(con, crop_id, product_id)`
- Tabel baru ditambahkan ke `SCHEMA` (CREATE TABLE IF NOT EXISTS) — tidak perlu `_MIGRATIONS` karena tabel baru, bukan kolom baru.

**Matcher** (`match()`): pakai `p["embeddings"]` (list) dan ambil similarity TERTINGGI.
Kompatibilitas: kalau produk hanya punya key `embedding` (dipakai di test lama & pemanggil
lain), perlakukan sebagai galeri berisi satu. Tulis test:
- galeri 2 entri: query mirip entri KEDUA → tetap match produk itu (skor dari entri terbaik)
- produk hanya punya `embedding` singular → tetap jalan (regresi)
- entri beda dimensi tetap di-skip (guard yang sudah ada)

Commit: `feat(db): galeri multi-embedding + tabel unknown_crops` dan
`feat(matcher): similarity tertinggi lintas galeri`

## Unit 2 — Pipeline simpan crop unknown

**Files:** `stoklens/photo.py`, `stoklens/scan.py`, `stoklens/crops.py` (baru), test

- `crops.py`: `simpan_crop(crop_bgr, scan_id, dir_dasar="data/crops") -> path` (buat dir, nama file unik, tulis JPEG via cv2). Test murni pakai array numpy + tmp_path.
- `scan_photos()` dan `run_scan()`: saat `match()` mengembalikan `pid is None`, simpan crop + embedding-nya lewat `db.add_unknown_crop`. Parameter baru `simpan_unknown=True` supaya bisa dimatikan di test.
- Batas wajar: simpan maksimal N crop unknown per scan (default 30) supaya tidak membanjiri disk saat model belum di-fine-tune. Test untuk batas ini.

Commit: `feat(scan): simpan crop item tak dikenali untuk enrollment`

## Unit 3 — API

**Files:** `stoklens/api.py`, `tests/test_api_unknown.py` (baru)

- Mount `/crops` → `StaticFiles(directory="data/crops")` (buat dir kalau belum ada).
- `GET /api/scans/{scan_id}/unknown` → `[{id, crop_url, created_at}]` (crop_url = `/crops/...`)
- `POST /api/unknown/{crop_id}/assign` body `{product_id}` → salin embedding crop ke
  `product_embeddings` (sumber `'scan'`) + `resolve_unknown_crop`. 404 kalau crop/produk
  tidak ada, 409 kalau crop sudah di-resolve. Response `{ok, product_id, jumlah_galeri}`.
- `POST /api/unknown/{crop_id}/produk-baru` body `{nama, harga_modal, harga_jual?,
  stok_minimum?, qty_awal?}` → buat produk baru memakai embedding crop sebagai embedding
  utama, lalu resolve crop ke produk itu. 409 kalau sudah di-resolve, 400 kalau nama duplikat.
- **Tidak boleh memuat CLIP** di ketiga endpoint ini (embedding sudah tersimpan) — test
  harus lulus tanpa torch di CI.

Commit: `feat(api): endpoint unknown crop — assign & produk baru`

## Unit 4 — UI

**Files:** `stoklens/webui/static/report_view.js`, `app.css`, test struktur

Di bawah tabel laporan, section **"Belum dikenali"** (hanya tampil kalau ada):
- Grid thumbnail crop (pakai `crop_url`), tiap crop tombol **"Ini barang apa?"**
- Tap → sheet: daftar produk (dari `/api/products`, dengan pencarian) + tombol
  "Barang baru" yang membuka form ringkas (nama, harga modal, harga jual opsional)
- Setelah berhasil: crop hilang dari grid + toast "Ditambahkan ke galeri <nama>"
- Pola wajib ikut yang ada: `api()`, `toast()`, `escapeHtml()`, `rp()`, `angka()`,
  state error "Gagal memuat" + "Coba lagi", target sentuh ≥48px, ikon Lucide inline,
  tanpa emoji, teks Indonesia.

Commit: `feat(ui): beri nama item tak dikenali dari laporan`

## Definisi selesai

Alur penuh di HP: scan foto → laporan menampilkan crop "Belum dikenali" → tap → pilih
produk / buat baru → scan berikutnya mengenali barang itu (karena galeri kini punya
referensi dalam kondisi scan yang sama).
