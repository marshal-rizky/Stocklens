"""FastAPI: enrollment, scan upload, report JSON, dashboard HTML."""
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, UploadFile
from fastapi.responses import HTMLResponse

from . import db
from .report import build_report


def _rp(n):
    return f"Rp{n:,.0f}".replace(",", ".")


def create_app(db_path="stoklens.db", embedder=None):
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
