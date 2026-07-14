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


@router.get("/opname")
def ui_opname(request: Request):
    return templates.TemplateResponse(request, "opname.html", {"aktif": "opname"})


@router.get("/laporan")
def ui_laporan(request: Request):
    return templates.TemplateResponse(request, "laporan.html", {"aktif": "laporan"})
