"""FastAPI: enrollment, scan, akuntansi stok (JSON API) + UI mobile (/ui/*).

Endpoint /api/* = kontrak untuk UI mobile (Google Stitch) — lihat docs/CATATAN-TIM.md.
"""
import csv
import io
import shutil
import sqlite3
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import accounting, crops, db
from .report import build_report
from .webui import router as webui_router

_STATIC_DIR = Path(__file__).parent / "webui" / "static"


class ProductPatch(BaseModel, extra="forbid"):
    nama: str | None = None
    harga_modal: int | None = None
    harga_jual: int | None = None
    stok_minimum: int | None = None


class UnknownAssign(BaseModel):
    product_id: int


class UnknownProdukBaru(BaseModel):
    nama: str
    harga_modal: int
    harga_jual: int | None = None
    stok_minimum: int = 0
    qty_awal: int = 0


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


def create_app(db_path="stoklens.db", embedder=None, photo_detector=None):
    """photo_detector: fn(image_bgr)->boxes untuk mode foto; None = YOLO asli."""
    app = FastAPI(title="StokLens")
    crops_prefix = crops.DIR_CROPS_DEFAULT.as_posix()

    def con():
        return db.connect(db_path)

    def get_embedder():
        nonlocal embedder
        if embedder is None:
            from .embedder import ClipEmbedder
            embedder = ClipEmbedder()
        return embedder

    app.include_router(webui_router)
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    # StaticFiles butuh direktori sudah ada saat mount — sengaja dibuat di sini
    # untuk SETIAP create_app(), bukan cuma yang perlu /crops. Efek samping ini
    # ditolerir (folder digitignore, "data/") demi tidak lazy-mount /crops.
    crops.DIR_CROPS_DEFAULT.mkdir(parents=True, exist_ok=True)
    app.mount("/crops", StaticFiles(directory=str(crops.DIR_CROPS_DEFAULT)), name="crops")

    @app.post("/products")
    async def create_product(nama: str = Form(...), harga_modal: int = Form(...),
                             qty_awal: int = Form(0),
                             harga_jual: int = Form(None),
                             stok_minimum: int = Form(0),
                             fotos: list[UploadFile] = None):
        from .enroll import enroll_product
        tmp = Path(tempfile.mkdtemp())
        paths = []
        for f in fotos:
            p = tmp / f.filename
            p.write_bytes(await f.read())
            paths.append(p)
        c = con()
        pid = enroll_product(c, get_embedder(), nama, harga_modal, paths,
                             harga_jual=harga_jual, qty_awal=qty_awal)
        if stok_minimum > 0:
            db.update_product(c, pid, stok_minimum=stok_minimum)
        shutil.rmtree(tmp, ignore_errors=True)
        return {"product_id": pid}

    @app.post("/scans")
    async def create_scan(video: UploadFile, lokasi_rak: str = Form(None),
                          count_mode: str = Form("line")):
        from .scan import run_scan
        tmp = Path(tempfile.mkdtemp()) / video.filename
        tmp.write_bytes(await video.read())
        sid = run_scan(con(), get_embedder(), tmp, lokasi_rak=lokasi_rak,
                       count_mode=count_mode)
        return {"scan_id": sid}

    @app.get("/report/{scan_id}")
    def report(scan_id: int):
        c = con()
        scan = db.get_scan(c, scan_id)
        if scan is None:
            raise HTTPException(404, "Scan tidak ditemukan")
        # Key "scan" tambahan (additive) — konsumen lama yang cuma baca
        # items/total_* tetap aman.
        return build_report(db.get_report_rows(c, scan_id)) | {
            "scan": scan,
        }

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
            db.mark_scan_applied(c, scan_id)
        return {"scan_id": scan_id, "diterapkan": body.terapkan, "report": rep}

    @app.get("/api/scans")
    def api_scans():
        c = con()
        out = []
        for s in db.list_scans(c):
            rep = build_report(db.get_report_rows(c, s["id"]))
            out.append(s | {
                "total_shrinkage_rp": rep["total_shrinkage_rp"],
                "total_rugi_expired_rp": rep["total_rugi_expired_rp"],
            })
        return out

    @app.post("/api/opname/{scan_id}/terapkan")
    def api_opname_terapkan(scan_id: int):
        c = con()
        scan = db.get_scan(c, scan_id)
        if scan is None:
            raise HTTPException(404, "Scan tidak ditemukan")
        # Guard terapkan ganda: snapshot lama tidak boleh menimpa stok sekarang.
        if scan["terapkan_pada"] is not None:
            raise HTTPException(409, "Opname ini sudah diterapkan")
        items = db.get_scan_items(c, scan_id)
        for item in items:
            db.set_stock(c, item["product_id"], item["qty_terdeteksi"],
                         sumber="opname", alasan=f"opname #{scan_id}")
        db.mark_scan_applied(c, scan_id)
        return {"ok": True, "jumlah_item": len(items)}

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

    # ---------- Unknown crops (enroll dari scan) ----------
    # PENTING: endpoint di bawah TIDAK BOLEH memanggil get_embedder() — embedding
    # sudah tersimpan di baris unknown_crops (Unit 1&2), jadi tidak perlu CLIP.

    @app.get("/api/scans/{scan_id}/unknown")
    def api_scan_unknown(scan_id: int):
        c = con()
        out = []
        for crop in db.list_unknown_crops(c, scan_id=scan_id, hanya_belum=True):
            out.append({
                "id": crop["id"],
                "crop_url": "/crops" + crop["crop_path"].removeprefix(crops_prefix),
                "created_at": crop["created_at"],
            })
        return out

    @app.post("/api/unknown/{crop_id}/assign")
    def api_unknown_assign(crop_id: int, body: UnknownAssign):
        c = con()
        crop = db.get_unknown_crop(c, crop_id)
        if crop is None:
            raise HTTPException(404, "Crop tidak ditemukan")
        if db.get_product(c, body.product_id) is None:
            raise HTTPException(404, "Produk tidak ditemukan")
        if crop["product_id"] is not None:
            raise HTTPException(409, "Crop ini sudah di-resolve")
        db.add_product_embedding(c, body.product_id, crop["embedding"], sumber="scan")
        db.resolve_unknown_crop(c, crop_id, body.product_id)
        return {
            "ok": True,
            "product_id": body.product_id,
            "jumlah_galeri": db.count_product_embeddings(c, body.product_id),
        }

    @app.post("/api/unknown/{crop_id}/produk-baru")
    def api_unknown_produk_baru(crop_id: int, body: UnknownProdukBaru):
        c = con()
        crop = db.get_unknown_crop(c, crop_id)
        if crop is None:
            raise HTTPException(404, "Crop tidak ditemukan")
        if crop["product_id"] is not None:
            raise HTTPException(409, "Crop ini sudah di-resolve")
        try:
            pid = db.add_product(c, body.nama, body.harga_modal, crop["embedding"],
                                 harga_jual=body.harga_jual)
        except sqlite3.IntegrityError as e:
            raise HTTPException(400, f"Nama produk '{body.nama}' sudah dipakai") from e
        if body.qty_awal:
            db.set_stock(c, pid, body.qty_awal)
        if body.stok_minimum > 0:
            db.update_product(c, pid, stok_minimum=body.stok_minimum)
        db.resolve_unknown_crop(c, crop_id, pid)
        return {"ok": True, "product_id": pid}

    @app.get("/")
    def root():
        return RedirectResponse(url="/ui/beranda")

    return app
