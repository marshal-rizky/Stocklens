# StokLens

Stock opname gudang pakai video HP: enrollment barang via foto (few-shot, tanpa retraining),
scan rak via YOLO + tracking + CLIP matching, baca tanggal expired via OCR, laporan selisih
stok + nilai rupiah di dashboard.

Prototype untuk AI Innovation Challenge COMPFEST 18.

**Anggota tim baru: baca [docs/CATATAN-TIM.md](docs/CATATAN-TIM.md) dulu** — peta modul,
keputusan desain + alasannya, mode hitung, parameter tuning, dan daftar pekerjaan tersisa.

## Menjalankan dengan Docker (cara tercepat)

Butuh Docker Desktop / Docker Engine dengan plugin Compose. Satu perintah, tanpa
menyiapkan Python:

```bash
docker compose up --build
```

Buka **http://localhost:8000** — otomatis diarahkan ke UI mobile di `/ui/beranda`.
Hentikan dengan `Ctrl+C`, lalu `docker compose down`.

Catatan penjalanan pertama:

- Build memasang **torch versi CPU** (sengaja — image jadi jauh lebih kecil, dan
  demo tidak butuh GPU). Untuk training tetap pakai GPU lokal, lihat
  [docs/PANDUAN-FINETUNE.md](docs/PANDUAN-FINETUNE.md).
- Bobot CLIP (±600 MB) dan EasyOCR diunduh saat **fitur terkait pertama dipakai**,
  bukan saat build — jadi enrollment pertama terasa lambat. Unduhan ini disimpan di
  volume `model-cache`, cukup sekali.
- Data opname (SQLite + crop hasil scan) ditulis ke folder `./data` di host, jadi
  tetap ada setelah `docker compose down`.
- Ukuran image ±2,2 GB (torch + ultralytics + easyocr). Build pertama ±2–10 menit
  tergantung koneksi.

Build image dan smoke test container dijalankan otomatis di GitHub Actions
(workflow **Docker**) setiap kali file terkait berubah — jadi kalau ada yang
merusaknya, ketahuan sebelum merge, tanpa perlu Docker di laptop masing-masing.

Menjalankan CLI di dalam container (server harus sedang jalan):

```bash
docker compose exec app python -m scripts.demo_scan report
```

## Install tanpa Docker (untuk yang mengembangkan kode)

```bash
pip install -r requirements.txt
```

Butuh Python 3.11. Instalasi pertama mengunduh bobot model (torch, CLIP, YOLO) —
butuh koneksi & waktu. Jalankan server:

```bash
uvicorn stoklens.api:create_app --factory
```

Lokasi file DB bisa diatur lewat env `STOKLENS_DB` (default `stoklens.db` di
direktori kerja). Untuk mengetes dari HP di WiFi yang sama, tambahkan
`--host 0.0.0.0` lalu buka `http://<IP-laptop>:8000`.

### Menukar bobot detektor — WAJIB dibaca sebelum uji lapangan

Bobot default `yolo11n.pt` adalah model **COCO** bawaan ultralytics: kelasnya
orang, mobil, anjing — **bukan produk retail**. Diukur pada foto rak warung
asli, `yolo11n` memberi **0 kotak**, sedangkan model hasil pre-train SKU-110K
memberi **33 kotak** pada foto yang sama.

Artinya: **kalau dijalankan apa adanya, scan tidak akan menemukan apa pun.**
Itu bukan tanda aplikasinya rusak — bobotnya saja yang belum diarahkan.

Arahkan lewat env `STOKLENS_MODEL`:

```bash
# Linux/macOS
STOKLENS_MODEL=/path/ke/best.pt uvicorn stoklens.api:create_app --factory

# Windows PowerShell
$env:STOKLENS_MODEL = "C:\Users\<kamu>\StokLens-training\pretrain_sku110k\weights\best.pt"
uvicorn stoklens.api:create_app --factory
```

Untuk Docker, tambahkan ke `environment:` di `docker-compose.yml` dan mount
folder bobotnya.

Catatan jujur soal akurasinya: SKU-110K dilatih di rak **supermarket**, jadi di
warung confidence-nya turun jauh — cukup untuk demo dan uji alur, belum cukup
untuk angka akurasi yang layak dipamerkan. Itu baru beres setelah fine-tune
dengan foto sendiri (`docs/PANDUAN-FINETUNE.md`).

## Tes

```bash
pytest                # test cepat (logika murni), tanpa model besar
pytest -m slow        # smoke test embedder/enrollment (download bobot CLIP)
```

## Alur demo

Jalankan dari **root repo**, dan perhatikan bentuk `python -m scripts.demo_scan` —
`python scripts/demo_scan.py` gagal dengan `ModuleNotFoundError: No module named
'stoklens'` karena paket `stoklens` tidak di-install (repo ini tanpa `pyproject.toml`).

```bash
# 0. PoC counting (tanpa enrollment, kelas COCO generik)
python -m scripts.poc_track video_rak.mp4

# 1. Daftarkan barang (3-5 foto per barang, sudut beda)
python -m scripts.demo_scan enroll --nama "Indomie Goreng" --harga 3200 --qty 40 --foto f1.jpg f2.jpg f3.jpg

# 2a. Opname via FOTO (mode default untuk toko kecil — 1 foto per sub-segmen rak)
python -m scripts.demo_scan scan-foto --foto rak1a.jpg rak1b.jpg --lokasi "Rak 1"

# 2b. Opname via VIDEO sweep (gudang besar; default count_mode=line,
#     kamera statis pakai --count-mode track — lihat docs/CATATAN-TIM.md)
python -m scripts.demo_scan scan --video rak1.mp4

# 3. Laporan terakhir
python -m scripts.demo_scan report

# 4. Dashboard web
uvicorn stoklens.api:create_app --factory
# buka http://127.0.0.1:8000
```

## Dokumentasi tim

| File | Isi |
|---|---|
| [docs/CATATAN-TIM.md](docs/CATATAN-TIM.md) | Peta modul, keputusan desain + alasannya, parameter tuning |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Rencana 28 hari ke deadline 25 Agustus 2026 |
| [STATUS.md](STATUS.md) | Papan status mingguan — siapa mengerjakan apa |
| [docs/CARA-KERJA-TIM.md](docs/CARA-KERJA-TIM.md) | Peran, aturan review, anti-konflik-semantik |
| [docs/PANDUAN-DATASET.md](docs/PANDUAN-DATASET.md) | SOP foto rak & labeling Roboflow |
| [docs/PANDUAN-FINETUNE.md](docs/PANDUAN-FINETUNE.md) | Alur fine-tune YOLO dua tahap |

## SOP perekaman (ringkas — detail di design doc §6)

1. Satu arah, jangan bolak-balik; kalau terlewat, ulang segmen dari awal.
2. Kecepatan lambat konsisten (±1 rak per 5–8 detik).
3. Jarak 50–80 cm, kamera tegak lurus rak.
4. Satu segmen rak = satu klip video.
5. Berhenti ±1 detik di tumpukan padat (untuk OCR expired).
6. Cahaya cukup, hindari backlight.
7. 1080p, 30fps, tanpa zoom digital.

Guided mode (produk per blok dideklarasikan dulu): pakai `--guided-product-id <id>` saat scan.
