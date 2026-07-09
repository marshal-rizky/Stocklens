"""CLI end-to-end StokLens.

Contoh:
  python scripts/demo_scan.py enroll --nama "Indomie Goreng" --harga 3200 \
      --qty 40 --foto foto1.jpg foto2.jpg
  python scripts/demo_scan.py scan --video rak1.mp4
  python scripts/demo_scan.py report --scan-id 1
"""
import argparse
import json

from stoklens import db
from stoklens.report import build_report

DB_PATH = "stoklens.db"


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
                       guided_product_id=args.guided_product_id)
        print(f"Scan selesai: id={sid}")
        print(json.dumps(build_report(db.get_report_rows(con, sid)),
                         indent=2, ensure_ascii=False))
    elif args.cmd == "report":
        sid = args.scan_id or db.latest_scan_id(con)
        print(json.dumps(build_report(db.get_report_rows(con, sid)),
                         indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
