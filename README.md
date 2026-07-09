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
