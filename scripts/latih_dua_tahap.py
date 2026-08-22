"""Fine-tune Step 2: dari checkpoint SKU-110K ke dataset warung sendiri.

Alur dua tahap sesuai docs/PANDUAN-FINETUNE.md — Step 1 (pre-train SKU-110K)
sudah dijalankan 28 Juli dan TIDAK diulang di sini; script ini memakai
checkpoint-nya sebagai titik awal.

Dua jebakan Windows yang sudah memakan korban, keduanya ditangani di sini:
- `project` DI LUAR repo: `stoklens/` adalah nama package Python-nya, hasil
  training tidak boleh menumpuk di dalam source.
- Semua di bawah `if __name__ == "__main__"`: DataLoader PyTorch di Windows
  memakai spawn dan meng-import ulang modul utama di tiap worker.

    python scripts/latih_dua_tahap.py
"""

import argparse
from pathlib import Path

AWAL = Path.home() / "StokLens-training" / "pretrain_sku110k" / "weights" / "best.pt"
DATA = "datasets/warung-merged/data.yaml"
KELUAR = Path.home() / "StokLens-training"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--awal", default=str(AWAL), help="checkpoint titik awal")
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--nama", default="finetune_dua_tahap")
    args = ap.parse_args()

    from ultralytics import YOLO

    if not Path(args.awal).exists():
        raise SystemExit(f"checkpoint tidak ada: {args.awal}")

    m = YOLO(args.awal)
    m.train(data=args.data, epochs=args.epochs, imgsz=640, batch=16,
            patience=15, workers=0, project=str(KELUAR), name=args.nama, plots=True)

    r = m.val(data=args.data, split="test", imgsz=640, workers=0, batch=4,
              verbose=False, project=str(KELUAR), name=args.nama + "_test")
    print(f"DUA_TAHAP mAP50={r.box.map50:.4f} mAP50-95={r.box.map:.4f} "
          f"P={r.box.mp:.4f} R={r.box.mr:.4f}", flush=True)
    print("SELESAI")


if __name__ == "__main__":
    main()
