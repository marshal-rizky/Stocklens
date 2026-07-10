"""FastAPI: enrollment, scan, akuntansi stok (JSON API) + dashboard HTML.

Endpoint /api/* = kontrak untuk UI mobile (Google Stitch) — lihat docs/CATATAN-TIM.md.
"""
import csv
import io
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from . import accounting, db
from .report import build_report


class ProductPatch(BaseModel, extra="forbid"):
    nama: str | None = None
    harga_modal: int | None = None
    harga_jual: int | None = None
    stok_minimum: int | None = None


class Adjustment(BaseModel):
    product_id: int
    delta: int
    alasan: str


class OpnameItem(BaseModel):
    product_id: int
    qty_fisik: int


class OpnameManual(BaseModel):
    items: list[OpnameItem]
    lokasi_rak: str | None = None
    terapkan: bool = False


def _rp(n):
    return f"Rp{n:,.0f}".replace(",", ".")


def create_app(db_path="stoklens.db", embedder=None, photo_detector=None):
    """photo_detector: fn(image_bgr)->boxes untuk mode foto; None = YOLO asli."""
    app = FastAPI(title="StokLens")

    def con():
        return db.connect(db_path)

    def get_embedder():
        nonlocal embedder
        if embedder is None:
            from .embedder import ClipEmbedder
            embedder = ClipEmbedder()
        return embedder

    @app.post("/products")
    async def create_product(nama: str = Form(...), harga_modal: int = Form(...),
                             qty_awal: int = Form(0),
                             fotos: list[UploadFile] = None):
        from .enroll import enroll_product
        tmp = Path(tempfile.mkdtemp())
        paths = []
        for f in fotos:
            p = tmp / f.filename
            p.write_bytes(await f.read())
            paths.append(p)
        pid = enroll_product(con(), get_embedder(), nama, harga_modal, paths,
                             qty_awal=qty_awal)
        shutil.rmtree(tmp, ignore_errors=True)
        return {"product_id": pid}

    @app.post("/scans")
    async def create_scan(video: UploadFile, lokasi_rak: str = Form(None)):
        from .scan import run_scan
        tmp = Path(tempfile.mkdtemp()) / video.filename
        tmp.write_bytes(await video.read())
        sid = run_scan(con(), get_embedder(), tmp, lokasi_rak=lokasi_rak)
        return {"scan_id": sid}

    @app.get("/report/{scan_id}")
    def report(scan_id: int):
        return build_report(db.get_report_rows(con(), scan_id))

    @app.post("/api/scans-foto")
    async def api_scan_foto(fotos: list[UploadFile], lokasi_rak: str = Form(None),
                            guided_product_id: int = Form(None),
                            read_expiry: bool = Form(True)):
        import cv2
        import numpy as np
        from .photo import scan_photos
        images = []
        for f in fotos:
            img = cv2.imdecode(np.frombuffer(await f.read(), np.uint8),
                               cv2.IMREAD_COLOR)
            if img is None:
                raise HTTPException(400, f"File bukan gambar valid: {f.filename}")
            images.append(img)
        c = con()
        sid = scan_photos(c, get_embedder(), images, detector=photo_detector,
                          guided_product_id=guided_product_id,
                          lokasi_rak=lokasi_rak, read_expiry=read_expiry)
        return {"scan_id": sid,
                "report": build_report(db.get_report_rows(c, sid))}

    # ---------- JSON API untuk UI mobile ----------

    def _product_row(p, stock_map):
        p = dict(p)
        p.pop("embedding", None)
        p.pop("foto_refs", None)
        p["qty"] = stock_map.get(p["id"], 0)
        p["margin_pct"] = accounting.margin_pct(p["harga_modal"], p.get("harga_jual"))
        return p

    @app.get("/api/products")
    def api_products():
        c = con()
        stock = db.get_stock_map(c)
        return [_product_row(p, stock) for p in db.all_products(c)]

    @app.get("/api/products/{product_id}")
    def api_product_detail(product_id: int):
        c = con()
        p = db.get_product(c, product_id)
        if p is None:
            raise HTTPException(404, "Produk tidak ditemukan")
        p = _product_row(p, db.get_stock_map(c))
        p["ledger"] = db.get_ledger(c, product_id)
        return p

    @app.patch("/api/products/{product_id}")
    def api_product_patch(product_id: int, patch: ProductPatch):
        c = con()
        if db.get_product(c, product_id) is None:
            raise HTTPException(404, "Produk tidak ditemukan")
        fields = {k: v for k, v in patch.model_dump().items() if v is not None}
        db.update_product(c, product_id, **fields)
        return {"ok": True}

    @app.post("/api/adjustments")
    def api_adjustment(adj: Adjustment):
        c = con()
        if db.get_product(c, adj.product_id) is None:
            raise HTTPException(404, "Produk tidak ditemukan")
        qty_lama = db.get_stock_map(c).get(adj.product_id, 0)
        try:
            qty_baru = accounting.apply_adjustment(qty_lama, adj.delta)
        except ValueError as e:
            raise HTTPException(400, str(e))
        db.set_stock(c, adj.product_id, qty_baru, sumber="penyesuaian",
                     alasan=adj.alasan)
        return {"qty_lama": qty_lama, "qty_baru": qty_baru}

    @app.post("/api/opname-manual")
    def api_opname_manual(body: OpnameManual):
        c = con()
        scan_id = db.add_scan(c, lokasi_rak=body.lokasi_rak, tipe="manual")
        for item in body.items:
            db.add_scan_item(c, scan_id, item.product_id, item.qty_fisik)
        rep = build_report(db.get_report_rows(c, scan_id))
        if body.terapkan:
            for item in body.items:
                db.set_stock(c, item.product_id, item.qty_fisik, sumber="opname",
                             alasan=f"opname #{scan_id}")
        return {"scan_id": scan_id, "diterapkan": body.terapkan, "report": rep}

    @app.get("/api/dashboard")
    def api_dashboard():
        c = con()
        products = [dict(p) for p in db.all_products(c)]
        stock = db.get_stock_map(c)
        sid = db.latest_scan_id(c)
        scan_terakhir = None
        if sid is not None:
            rep = build_report(db.get_report_rows(c, sid))
            scan_terakhir = db.get_scan(c, sid) | {
                "total_shrinkage_rp": rep["total_shrinkage_rp"],
                "total_rugi_expired_rp": rep["total_rugi_expired_rp"],
            }
        return {
            "nilai_stok_rp": accounting.nilai_stok(products, stock),
            "potensi_laba_rp": accounting.potensi_laba(products, stock),
            "stok_menipis": accounting.stok_menipis(products, stock),
            "scan_terakhir": scan_terakhir,
        }

    @app.get("/api/export/stok.csv", response_class=PlainTextResponse)
    def api_export_stok():
        c = con()
        stock = db.get_stock_map(c)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "nama", "qty", "harga_modal", "harga_jual",
                    "margin_pct", "nilai_stok_rp"])
        for p in db.all_products(c):
            qty = stock.get(p["id"], 0)
            w.writerow([p["id"], p["nama"], qty, p["harga_modal"],
                        p["harga_jual"] or "",
                        accounting.margin_pct(p["harga_modal"], p["harga_jual"]) or "",
                        qty * p["harga_modal"]])
        return PlainTextResponse(
            buf.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=stok.csv"})

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        c = con()
        sid = db.latest_scan_id(c)
        if sid is None:
            return "<h1>StokLens</h1><p>Belum ada scan.</p>"
        rep = build_report(db.get_report_rows(c, sid))
        rows = "".join(
            f"<tr><td>{i['nama']}</td><td>{i['qty_tercatat']}</td>"
            f"<td>{i['qty_terdeteksi']}</td><td>{i['selisih']}</td>"
            f"<td>{_rp(i['shrinkage_rp'])}</td><td>{i['expired_terdekat'] or '-'}</td>"
            f"<td>{_rp(i['rugi_expired_rp'])}</td></tr>"
            for i in rep["items"]
        )
        return f"""<html><head><title>StokLens</title><style>
        body{{font-family:sans-serif;margin:2rem}} table{{border-collapse:collapse}}
        td,th{{border:1px solid #ccc;padding:.4rem .8rem}} .kpi{{display:inline-block;
        margin-right:2rem;padding:1rem;border:1px solid #ccc;border-radius:8px}}
        </style></head><body><h1>StokLens — Scan #{sid}</h1>
        <div class="kpi">Nilai stok<br><b>{_rp(rep['total_nilai_rp'])}</b></div>
        <div class="kpi">Shrinkage<br><b>{_rp(rep['total_shrinkage_rp'])}</b></div>
        <div class="kpi">Potensi rugi expired<br><b>{_rp(rep['total_rugi_expired_rp'])}</b></div>
        <table><tr><th>Produk</th><th>Tercatat</th><th>Terdeteksi</th><th>Selisih</th>
        <th>Shrinkage</th><th>Expired terdekat</th><th>Rugi expired</th></tr>{rows}</table>
        </body></html>"""

    return app
