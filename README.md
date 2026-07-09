# StokLens

Stock opname gudang pakai video HP: enrollment barang via foto (few-shot, tanpa retraining),
scan rak via YOLO + tracking + CLIP matching, baca tanggal expired via OCR, laporan selisih
stok + nilai rupiah di dashboard.

Prototype untuk AI Innovation Challenge COMPFEST 18.

## Install

```bash
pip install -r requirements.txt
```

Instalasi pertama mengunduh bobot model (torch, CLIP, YOLO) — butuh koneksi & waktu.

## Tes

```bash
pytest                # test cepat (logika murni), tanpa model besar
pytest -m slow        # smoke test embedder/enrollment (download bobot CLIP)
```

## Alur demo

```bash
# 0. PoC counting (tanpa enrollment, kelas COCO generik)
python scripts/poc_track.py video_rak.mp4

# 1. Daftarkan barang (3-5 foto per barang, sudut beda)
python scripts/demo_scan.py enroll --nama "Indomie Goreng" --harga 3200 --qty 40 --foto f1.jpg f2.jpg f3.jpg

# 2. Scan video rak
python scripts/demo_scan.py scan --video rak1.mp4

# 3. Laporan terakhir
python scripts/demo_scan.py report

# 4. Dashboard web
uvicorn stoklens.api:create_app --factory
# buka http://127.0.0.1:8000
```

## SOP perekaman (ringkas — detail di design doc §6)

1. Satu arah, jangan bolak-balik; kalau terlewat, ulang segmen dari awal.
2. Kecepatan lambat konsisten (±1 rak per 5–8 detik).
3. Jarak 50–80 cm, kamera tegak lurus rak.
4. Satu segmen rak = satu klip video.
5. Berhenti ±1 detik di tumpukan padat (untuk OCR expired).
6. Cahaya cukup, hindari backlight.
7. 1080p, 30fps, tanpa zoom digital.

Guided mode (produk per blok dideklarasikan dulu): pakai `--guided-product-id <id>` saat scan.
