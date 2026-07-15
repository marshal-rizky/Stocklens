"""Router UI mobile (Jinja2, server-rendered). Konsumsi /api/* lewat app.js."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(_DIR / "templates"))

router = APIRouter(prefix="/ui")


@router.get("/beranda")
def ui_beranda(request: Request):
    return templates.TemplateResponse(request, "beranda.html", {"aktif": "beranda"})


@router.get("/barang")
def ui_barang(request: Request):
    return templates.TemplateResponse(request, "barang.html", {"aktif": "barang"})


@router.get("/barang/baru")
def ui_barang_baru(request: Request):
    return templates.TemplateResponse(request, "barang_baru.html", {"aktif": "barang"})


@router.get("/barang/{product_id}")
def ui_barang_detail(request: Request, product_id: int):
    return templates.TemplateResponse(
        request, "barang_detail.html",
        {"aktif": "barang", "product_id": product_id},
    )


@router.get("/opname")
def ui_opname(request: Request):
    return templates.TemplateResponse(request, "opname.html", {"aktif": "opname"})


@router.get("/opname/manual")
def ui_opname_manual(request: Request):
    return templates.TemplateResponse(request, "opname_manual.html", {"aktif": "opname"})


@router.get("/opname/foto")
def ui_opname_foto(request: Request):
    return templates.TemplateResponse(request, "opname_foto.html", {"aktif": "opname"})


@router.get("/opname/video")
def ui_opname_video(request: Request):
    return templates.TemplateResponse(request, "opname_video.html", {"aktif": "opname"})


@router.get("/laporan")
def ui_laporan(request: Request):
    return templates.TemplateResponse(request, "laporan.html", {"aktif": "laporan"})


@router.get("/laporan/{scan_id}")
def ui_laporan_detail(request: Request, scan_id: int):
    return templates.TemplateResponse(
        request, "laporan_detail.html",
        {"aktif": "laporan", "scan_id": scan_id},
    )
