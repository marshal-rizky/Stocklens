# StokLens — image untuk menjalankan aplikasi lengkap secara lokal.
# Dipakai oleh docker-compose.yml (deliverable wajib rulebook AIC).
# Suite Debian di-pin eksplisit. Tag `python:3.11-slim` sudah berpindah dari
# bookworm ke trixie tanpa pengumuman; menjelang deadline, base image tidak boleh
# berubah di bawah kaki kami.
FROM python:3.11-slim-trixie

# opencv-python butuh dua library sistem ini di image slim. Tanpa keduanya
# `import cv2` gagal dengan "libGL.so.1: cannot open shared object file" —
# error-nya muncul saat runtime, bukan saat build, jadi gampang kelewat.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch CPU-only dipasang DULUAN dan sengaja dari index cpu: wheel default di
# PyPI membawa seluruh runtime CUDA (>2 GB) yang tidak ada gunanya di container
# demo — juri menjalankan ini di laptop, bukan mesin ber-GPU. Untuk training
# tetap pakai GPU lokal, lihat docs/PANDUAN-FINETUNE.md.
#
# Versinya di-pin dan disamakan dengan mesin dev tim (yang memakai varian +cu126).
# Tanpa pin, image yang di-build hari-H bisa berbeda dari yang pernah diuji.
# ultralytics/open_clip/easyocr semuanya cuma minta batas bawah (torch>=2.0), jadi
# `pip install -r requirements.txt` di bawah TIDAK akan menarik ulang wheel CUDA —
# selama pin ini tetap memenuhi batas bawah tersebut. Kalau suatu saat requirements
# menaikkan lantai versi torch, naikkan juga pin di sini, jangan biarkan pip
# diam-diam mengambil wheel CUDA dari PyPI.
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.13.0" "torchvision==0.28.0"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DB dan crop hasil scan ditulis ke /app/data — di-mount sebagai volume oleh
# compose supaya tidak hilang saat container dibuat ulang.
#
# EASYOCR_MODULE_PATH: EasyOCR default-nya menyimpan bobot di ~/.EasyOCR, DI LUAR
# ~/.cache, jadi tanpa baris ini volume cache compose tidak menangkapnya dan
# bobot OCR (±60–100 MB) diunduh ulang tiap container dibuat ulang.
ENV STOKLENS_DB=/app/data/stoklens.db \
    EASYOCR_MODULE_PATH=/root/.cache/easyocr \
    PYTHONUNBUFFERED=1

# Catatan yang sengaja TIDAK diperbaiki: `yolo11n.pt` diunduh ultralytics ke cwd
# (/app), bukan ke ~/.cache, jadi ikut hilang saat container dibuat ulang.
# Ukurannya ±5,5 MB — biaya unduh ulangnya tidak sepadan dengan menambah
# konfigurasi. Yang perlu diketahui: start pertama tiap container butuh jaringan.

EXPOSE 8000

CMD ["uvicorn", "stoklens.api:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
