# Catatan Tim StokLens

> Dokumen onboarding untuk anggota tim. Baca ini dulu sebelum menyentuh kode.
> Update terakhir: 2026-07-28.

## Apa ini

StokLens = stock opname gudang pakai video HP, untuk **AI Innovation Challenge COMPFEST 18**
(kategori Smart Logistics, tema "AI for the Backbone of the Economy", partner WIZ.AI).

Alur produk: daftarkan barang lewat foto (sekali per barang) → rekam video sweep rak →
AI menghitung stok per barang + baca tanggal expired → laporan selisih vs catatan +
nilai rupiah di dashboard.

Dokumen terkait **di repo ini** (baca sesuai kebutuhan):
- `ROADMAP.md` — rencana 28 hari sampai deadline 25 Agustus. **Baca kedua, setelah file ini.**
- `CARA-KERJA-TIM.md` — peran, aturan review, anti-konflik-semantik
- `AUDIT-RULEBOOK-2026-07-28.md` — audit terhadap rulebook + rincian bobot penilaian
- `PANDUAN-DATASET.md` / `PANDUAN-FINETUNE.md` — SOP foto & labeling, alur fine-tune
- `BACKLOG.md` — perbaikan yang ditunda (**bukan** daftar kerjaan bebas, baca peringatannya)
- `plans/` — plan doc per fitur + catatan review; sumber cerita iteratif untuk proposal

Dokumen di luar repo (minta ke ketua tim):
- **Design doc (spec)** `2026-07-09-stoklens-design.md` & **implementation plan**
  `2026-07-09-stoklens-prototype.md` — keputusan desain awal. Ringkasan yang masih
  relevan sudah disalin ke file ini, jadi tidak wajib untuk mulai kerja.
- **Rulebook AIC** `[AIC] AI Innovation Challenge.pdf` — WAJIB baca. Poin krusial:
  model harus di-fine-tune, MVP tidak boleh overbuilt, Conventional Commits wajib.

## Setup dari nol

```bash
# Python 3.11
pip install -r requirements.txt   # download besar (~2GB, torch dkk), sekali saja
pytest                            # seluruh test cepat, harus hijau, ±3 detik
pytest -m slow                    # 2 smoke test model (download bobot CLIP sekali, ±600MB)
```

Kalau `pytest` merah di kondisi repo bersih → lapor di grup, jangan didiamkan.

> Docs ini **sengaja tidak menyebut jumlah test**. Angkanya pernah ditulis di tiga
> file dengan tiga nilai berbeda (31 / 56 / 82) dan ketiganya salah — jumlah test
> berubah tiap PR, jadi angka apa pun yang ditulis pasti basi. Butuh angkanya
> (misal untuk proposal)? Jalankan `pytest -q --collect-only` saat itu juga.

## Peta modul

| File | Tanggung jawab | Test |
|---|---|---|
| `stoklens/expiry.py` | Parser tanggal expired dari teks OCR (format Indonesia: EXP/ED/BAIK SEBELUM, nama bulan ID) | `test_expiry.py` |
| `stoklens/db.py` | SQLite: products (embedding BLOB), scans, scan_items, stock_ledger, product_embeddings (galeri enroll-dari-scan), unknown_crops | `test_db.py` |
| `stoklens/matcher.py` | Cosine matching crop→galeri produk (ambil similarity TERTINGGI lintas galeri, bukan rata-rata), majority vote per track, guided mode | `test_matcher.py` |
| `stoklens/crops.py` | Simpan file crop item tak dikenali ke `data/crops/<scan_id>/`, path dicatat di DB, disajikan lewat mount `/crops` | `test_crops.py` |
| `stoklens/counter.py` | Agregasi track → qty per produk, filter track pendek | `test_counter.py` |
| `stoklens/crossing.py` | **Line-crossing counting** — anti dobel hitung (baca docstring-nya, panjang & penting) | `test_crossing.py` |
| `stoklens/report.py` | Selisih fisik vs tercatat → rupiah (shrinkage, rugi expired, nilai stok) | `test_report.py` |
| `stoklens/frames.py` | Iterasi frame video dengan sampling | `test_frames.py` |
| `stoklens/embedder.py` | Wrapper CLIP (open_clip ViT-B-32) → embedding 512-dim ternormalisasi | `test_embedder_slow.py` |
| `stoklens/ocr.py` | Wrapper EasyOCR (lazy singleton) | — (diuji via lapangan) |
| `stoklens/enroll.py` | Foto barang → rata-rata embedding → DB | `test_enroll_slow.py` |
| `stoklens/scan.py` | Orkestrasi: video → YOLO+BoT-SORT → match → OCR → DB | — (glue; logika intinya sudah diuji di modul lain) |
| `stoklens/api.py` | FastAPI: JSON API (/api/*, /products, /scans, /report) + mount UI | `test_api.py`, `test_api_ui.py` |
| `stoklens/webui/` | UI mobile (/ui/*): templates Jinja2 + JS vanilla; GET / redirect ke /ui/beranda | `test_webui.py` |
| `stoklens/botsort_reid.yaml` | Config tracker anti ID-pecah (baca komentarnya) | — |
| `scripts/poc_track.py` | PoC counting pakai YOLO pretrained (kelas COCO) — untuk validasi awal | — |
| `scripts/demo_scan.py` | CLI end-to-end: enroll / scan / report | — |

Aturan main: **logika murni dipisah dari wrapper model berat** supaya bisa dites tanpa
GPU/download. Kalau nambah logika, tulis test-nya (lihat pola test yang ada), taruh di
modul murni, jangan ditanam di `scan.py`.

## Alur data lengkap

```
[Enrollment]  foto 3–5 sudut ─ClipEmbedder→ embedding rata-rata ─→ products (DB)
                                            + nama, harga modal/jual, stok awal

[Scan]  video sweep ─YOLO+BoT-SORT(ReID)→ track per objek
        tiap track: crop → embedding (tiap `embed_every` frame)
                    → match cosine ke galeri → majority vote = label track
        posisi-x track → line-crossing → track dihitung / tidak
        → aggregate() → qty per produk
        crop terbesar per track → EasyOCR → parse_expiry() → tanggal expired

[Output]  scan_items (DB) → build_report(): selisih vs stock_ledger,
          shrinkage Rp, rugi expired Rp → UI mobile (/ui/beranda, /ui/laporan) / JSON (GET /report/{id})
```

## Keputusan desain penting + ALASANNYA (jangan diulang debatnya tanpa data baru)

1. **Deteksi generik + CLIP matching, BUKAN classifier per-SKU.**
   Barang baru cukup difoto (enrollment), nol retraining di lapangan. Ini selling point
   utama produk. Konsekuensi: kualitas matching bergantung foto enrollment.

2. **Hitungan per track ID, bukan per deteksi.**
   Counter tidak naik cuma karena barang terlihat; satu track = satu barang.

3. **Anti dobel hitung berlapis** (concern: ID pecah → dobel):
   - Lapisan 1: filter `min_track_frames` (track pendek = noise).
   - Lapisan 2: BoT-SORT + ReID + `track_buffer: 60` (`botsort_reid.yaml`) — ID putus
     disambung pakai kemiripan visual; barang ketutupan ±2 detik tidak jadi ID baru.
   - Lapisan 3: **line-crossing** (`crossing.py`, default `count_mode="line"`) — track
     dihitung hanya saat menyeberang garis tengah layar searah sweep; hysteresis
     menyerap jitter; nyebrang balik = minus (self-correcting).
   - Kalau uji lapangan MASIH dobel: opsi lanjutan = merge spatio-temporal
     (gabung track yang TIDAK pernah hidup bersamaan + posisi dekat + embedding mirip).

4. **Dedup pakai embedding similarity SAJA itu DILARANG.**
   Dua dus Indomie berbeda punya embedding hampir identik → dedup embedding-only
   menghapus hitungan yang benar. Sudah dianalisis, jangan diimplement ulang.

5. **Guided mode** (`--guided-product-id`): user deklarasi produk per blok sebelum sweep
   → matching jadi verifikasi, bukan tebakan. Pakai untuk varian kemasan mirip
   (Indomie goreng vs soto).

6. **EasyOCR, bukan PaddleOCR** (deviasi dari spec): satu stack torch, instalasi Windows
   gampang. Boleh ditukar kalau ada yang sanggup benchmark.

7. **Brute-force cosine numpy, bukan FAISS/sqlite-vec**: untuk ≤ ratusan SKU tidak perlu
   (YAGNI). Revisit kalau katalog ribuan.

## Mode foto vs video — pilih capture yang tepat

| | 📷 Foto (default toko kecil) | 🎥 Video (gudang besar) |
|---|---|---|
| Cara | 1 foto per sub-segmen rak (berbatas tiang/sekat) | Sweep satu arah per segmen |
| Dobel hitung | Dalam 1 foto: mustahil. Antar foto: jangan overlap (SOP) + review `per_foto` di UI | Ditangani tracking + ReID + line-crossing |
| Biaya/kuota | ±3 MB per foto | ±75 MB per segmen |
| OCR expired | Tajam (foto diam) ✅ | Sering blur ⚠️ |
| Kecepatan capture | Lebih lambat (framing per foto) | Cepat (30 dtk/segmen) |
| Modul | `photo.py` (`scan_photos`) | `scan.py` (`run_scan`) |

SOP foto: 1 foto = 1 sub-segmen dengan batas fisik; mulai foto berikutnya DARI batas
tersebut, jangan tumpang tindih; ambil close-up terpisah untuk tanggal expired.

```bash
python -m scripts.demo_scan scan-foto --foto rak1a.jpg rak1b.jpg --lokasi "Rak 1"
```

## Mode hitung video — WAJIB paham sebelum demo

| Mode | Kapan | Perilaku |
|---|---|---|
| `line` (default) | Rekaman sweep sesuai SOP | Hanya track yang menyeberang garis tengah searah sweep yang dihitung. **Kamera statis = hitungan 0** (bukan bug!) |
| `track` | Kamera statis / video uji di meja | Semua track lolos filter dihitung |

```bash
python -m scripts.demo_scan scan --video rak.mp4                     # sweep (default line)
python -m scripts.demo_scan scan --video meja.mp4 --count-mode track  # statis
```

## Parameter tuning saat uji lapangan

| Parameter | Default | Naikkan kalau | Turunkan kalau |
|---|---|---|---|
| `match_threshold` | 0.75 | banyak salah-label antar varian | banyak masuk "unknown" |
| `min_track_frames` | 3 | masih ada hitungan hantu | barang gerak cepat tidak terhitung |
| `embed_every` | 5 | scan lambat | matching kurang stabil |
| `hysteresis` (crossing) | 0.05 | jitter garis masih bikin event | barang di dekat garis tidak terhitung |
| `track_buffer` (yaml) | 60 | ID masih pecah saat ketutupan lama | ID "nyangkut" ke barang lain |

Catat SETIAP perubahan + hasilnya (video uji → hitungan vs manual) di sheet uji lapangan.

> **Angka uji yang sudah ada: `HASIL-UJI-2026-08-02.md`.** Baca sebelum menyetel
> apa pun atau sebelum menulis klaim akurasi di proposal/video. Tiga hal yang
> paling sering salah dikira di situ: (1) guided mode **tidak** menaikkan akurasi
> — ia cuma mempersempit kandidat; (2) menambah entri galeri hampir tidak
> berpengaruh — satu entri dari kondisi pemotretan yang mirip (0,823) mengalahkan
> dua belas entri dari kondisi berbeda (0,664), karena matching mengambil
> similarity TERTINGGI; (3) angka apa pun yang foto ujinya ikut menyumbang entri
> galeri adalah self-match dan tidak boleh dipakai — termasuk lewat foto
> enrollment, yang sempat membuat satu kesimpulan di dokumen itu keliru.

## SOP perekaman (versi ringkas — lengkap di design doc §6)

Satu arah • 1 rak per 5–8 detik • jarak 50–80 cm tegak lurus • 1 segmen = 1 klip •
pause 1 detik di tumpukan padat • cahaya cukup • 1080p 30fps tanpa zoom.

## Alur kerja Git (repo: github.com/marshal-rizky/Stocklens)

> Ringkas. Aturan lengkap — siapa boleh merge, checklist reviewer, aturan
> anti-konflik-semantik — ada di `CARA-KERJA-TIM.md`. Kalau dua dokumen ini beda,
> `CARA-KERJA-TIM.md` yang menang.

1. **Jangan commit langsung ke `main`.** Bikin branch per fitur: `git checkout -b fitur/nama-fitur`.
2. Sebelum mulai kerja: `git pull origin main` dulu — mulai dari kode terbaru.
3. Commit kecil & sering, push, buka **Pull Request** — minimal 1 orang lain melihat sebelum merge.
4. PR hanya boleh merge kalau **CI hijau** (pytest jalan otomatis di GitHub Actions).
5. Branch umur pendek (1–3 hari). Kalau `main` sudah maju: `git pull origin main` ke branch-mu, selesaikan konflik di situ, jalankan `pytest`, baru merge.
6. **Yang TIDAK boleh masuk git** (sudah di-.gitignore, jangan di-force): `*.db`, bobot model `*.pt`, video/foto uji, dataset. Share lewat Drive/Roboflow.
7. Pembagian kerja ikuti batas file/folder (lihat peta modul) — dua orang di file yang sama = ngobrol dulu di grup.



## Pekerjaan tersisa (ambil, tulis nama di grup)

> **Batas keras sejak 2026-07-28:** alur inti (enroll → scan → laporan selisih) sudah
> lengkap dan rulebook AIC menilai MVP yang *overbuilt* secara **negatif**. Daftar di
> bawah sengaja tidak berisi fitur baru. Jadwal harian yang mengikat ada di
> `ROADMAP.md` (28 hari ke 25 Agustus); aturan kerjanya di `CARA-KERJA-TIM.md`.

1. **Uji PoC** (bisa hari ini, tanpa dataset): rekam video rak/lemari →
   `python -m scripts.poc_track video.mp4` → validasi counting masuk akal.
2. **Uji end-to-end kecil**: enroll 3–5 barang dapur/warung → scan → cek dashboard.
   Catat akurasi hitungan vs manual. Ini bahan kalibrasi parameter di atas.
3. **Dataset gudang** (paling besar): izin 2–3 toko grosir → rekam → label 20–30 SKU
   di Roboflow (~500–1000 frame). Target: dataset siap sebelum fine-tune.
   Baca `PANDUAN-DATASET.md` §"Kondisi foto" dulu — salah kondisi foto = dataset terbuang.
4. **Fine-tune YOLO** jadi detektor "produk retail" generik (WAJIB per rulebook) —
   laptop ketua (RTX 4070) cukup, YOLO11n/s ±50 epoch. Lihat `PANDUAN-FINETUNE.md`.
5. **Uji lapangan enroll-dari-scan**: kodenya lengkap tapi belum pernah dijalankan di
   HP dengan barang sungguhan (lihat `plans/2026-07-18-enroll-dari-scan.md`).
6. **Proposal PDF + 2 video** — bobot gabungan 30%, belum disentuh. Ini pekerjaan
   dengan rasio nilai/effort tertinggi yang tersisa, bukan koding.

**Ditunda sampai penyisihan lewat (JANGAN dikerjakan sekarang):** fine-tune CLIP
(opsional — syarat rulebook sudah dipenuhi YOLO) • poles dashboard/UI • fitur apa pun
di luar alur inti. Alasannya di `ROADMAP.md` §"Scope penyisihan".

## FAQ juri (siapkan jawaban ini di pitch)

- *"Barang di belakang ketutupan?"* → hitung facing + konfigurasi kedalaman rak;
  produk ini alat opname cepat, bukan pengganti audit total.
- *"Kalau dobel hitung?"* → jelaskan 3 lapisan (ReID, track_buffer, line-crossing).
- *"Kenapa bukan barcode/RFID?"* → RFID mahal per item, barcode scan satu-satu;
  kamera = satu kali jalan, nol hardware tambahan.
- *"Bedanya sama WMS?"* → zero hardware, zero barcode discipline, harga UMKM.
- *"Model fine-tune di mana?"* → YOLO (detektor produk retail Indonesia) + CLIP
  (metric learning kemasan lokal); tunjukkan kurva training.
