"""CLI end-to-end StokLens.

WAJIB dijalankan dengan `python -m scripts.demo_scan`, dari root repo.
`python scripts/demo_scan.py` GAGAL (`ModuleNotFoundError: No module named
'stoklens'`) karena Python menaruh `scripts/` di sys.path[0], bukan root repo,
dan paket `stoklens` tidak di-install (repo ini tanpa pyproject/setup.py).

Contoh:
  python -m scripts.demo_scan enroll --nama "Indomie Goreng" --harga 3200 \
      --qty 40 --foto foto1.jpg foto2.jpg
  python -m scripts.demo_scan scan --video rak1.mp4
  python -m scripts.demo_scan report --scan-id 1
"""
import argparse
import json
import os

from stoklens import db
from stoklens.report import build_report

# Sama seperti create_app(): env `STOKLENS_DB` supaya CLI dan server menunjuk
# file DB yang sama, termasuk saat dijalankan lewat `docker compose exec`.
DB_PATH = os.environ.get("STOKLENS_DB", "stoklens.db")


def _embedder():
    from stoklens.embedder import ClipEmbedder
    return ClipEmbedder()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enroll")
    e.add_argument("--nama", required=True)
    e.add_argument("--harga", type=int, required=True)
    e.add_argument("--qty", type=int, default=0)
    e.add_argument("--foto", nargs="+", required=True)

    s = sub.add_parser("scan")
    s.add_argument("--video", required=True)
    s.add_argument("--guided-product-id", type=int, default=None)
    s.add_argument("--count-mode", choices=["line", "track"], default="line",
                   help="line: rekaman sweep (anti dobel); track: kamera statis")

    sf = sub.add_parser("scan-foto",
                        help="opname via foto per sub-segmen (mode default toko kecil)")
    sf.add_argument("--foto", nargs="+", required=True)
    sf.add_argument("--guided-product-id", type=int, default=None)
    sf.add_argument("--lokasi", default=None)

    r = sub.add_parser("report")
    r.add_argument("--scan-id", type=int, default=None)

    args = ap.parse_args()
    con = db.connect(DB_PATH)

    if args.cmd == "enroll":
        from stoklens.enroll import enroll_product
        pid = enroll_product(con, _embedder(), args.nama, args.harga,
                             args.foto, qty_awal=args.qty)
        print(f"Terdaftar: {args.nama} (id={pid}, stok awal={args.qty})")
    elif args.cmd == "scan":
        from stoklens.scan import run_scan
        sid = run_scan(con, _embedder(), args.video,
                       guided_product_id=args.guided_product_id,
                       count_mode=args.count_mode)
        print(f"Scan selesai: id={sid}")
        print(json.dumps(build_report(db.get_report_rows(con, sid)),
                         indent=2, ensure_ascii=False))
    elif args.cmd == "scan-foto":
        from stoklens.photo import scan_photos
        sid = scan_photos(con, _embedder(), args.foto,
                          guided_product_id=args.guided_product_id,
                          lokasi_rak=args.lokasi)
        print(f"Scan foto selesai: id={sid}")
        print(json.dumps(build_report(db.get_report_rows(con, sid)),
                         indent=2, ensure_ascii=False))
    elif args.cmd == "report":
        sid = args.scan_id or db.latest_scan_id(con)
        print(json.dumps(build_report(db.get_report_rows(con, sid)),
                         indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
