"""FastAPI: enrollment, scan, akuntansi stok (JSON API) + UI mobile (/ui/*).

Endpoint /api/* = kontrak untuk UI mobile (Google Stitch) — lihat docs/CATATAN-TIM.md.
"""
import base64
import csv
import io
import os
import secrets
import shutil
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Response, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import accounting, crops, db, penamaan
from .report import build_report
from .webui import router as webui_router

_STATIC_DIR = Path(__file__).parent / "webui" / "static"

# Batas untuk /api/scans-foto. Yang dijaga RAM, bukan disk: cv2.imdecode
# menghasilkan array BGR tak terkompresi (foto 12 MP ≈ 36 MB), dan scan_photos
# menahan SEMUA foto sekaligus karena dedup-nya lintas foto. Tanpa batas, 60
# foto ≈ 2 GB dan laptop demo kehabisan memori.
MAKS_FOTO_PER_SCAN = 20                 # satu rak nyatanya 3–10 foto
MAKS_BYTE_PER_FOTO = 15 * 1024 * 1024   # JPEG 12 MP HP ≈ 5 MB, jadi lapang


def _galat_foto_terlalu_besar(nama_file, ukuran) -> HTTPException:
    # Dipakai dua kali (jalur f.size dan jalur len(data)); angka batasnya dibaca
    # dari konstanta supaya pesan ikut kalau batasnya disetel ulang.
    return HTTPException(
        400, f"Foto {nama_file} terlalu besar ({ukuran / 1024 / 1024:.1f} MB), "
             f"maksimal {MAKS_BYTE_PER_FOTO // (1024 * 1024)} MB")


def _gambar_valid(path) -> bool:
    """True kalau berkas benar-benar gambar yang bisa dibuka.

    Pakai PIL.verify() dan bukan cv2.imread: enroll_product juga membuka foto
    lewat PIL, jadi yang divalidasi harus pustaka yang sama — kalau tidak, ada
    berkas yang lolos di sini tapi tetap meledak beberapa baris kemudian.
    """
    from PIL import Image
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


# ge=0 di seluruh field angka: harga dan stok negatif tidak punya arti, dan
# sebelumnya diterima diam-diam — harga_modal negatif membuat shrinkage jadi
# angka negatif yang tampil sebagai "kerugian" yang tidak masuk akal.
class ProductPatch(BaseModel, extra="forbid"):
    nama: str | None = None
    harga_modal: int | None = Field(default=None, ge=0)
    harga_jual: int | None = Field(default=None, ge=0)
    stok_minimum: int | None = Field(default=None, ge=0)


class UnknownAssign(BaseModel):
    product_id: int


class UnknownProdukBaru(BaseModel):
    nama: str
    harga_modal: int = Field(ge=0)
    harga_jual: int | None = Field(default=None, ge=0)
    stok_minimum: int = Field(default=0, ge=0)
    qty_awal: int = Field(default=0, ge=0)


class Adjustment(BaseModel):
    product_id: int
    delta: int
    alasan: str


class OpnameItem(BaseModel):
    product_id: int
    # ge=0: sebelumnya qty_fisik negatif lolos dan menulis stok ledger jadi
    # negatif — padahal /api/adjustments sudah menjaga hal yang sama lewat
    # accounting.apply_adjustment. Ini menutup ketidakkonsistenannya.
    qty_fisik: int = Field(ge=0)


class OpnameManual(BaseModel):
    items: list[OpnameItem]
    lokasi_rak: str | None = None
    terapkan: bool = False


def _pasang_guard(app):
    """Kunci seluruh app pakai HTTP Basic kalau STOKLENS_PASSWORD di-set.

    Dipakai saat app diekspos ke internet (tunnel ke PC, atau deploy). Tanpa ini
    siapa pun yang menemukan URL-nya bisa membaca buku stok, mengubah harga,
    menerapkan opname, dan mengunggah file. URL tunnel acak bukan pengaman —
    ia tidak rahasia, cuma belum ditebak.

    Basic auth, bukan halaman login: browser HP menanganinya sendiri, jadi nol
    perubahan di JS dan `fetch()` ikut terautentikasi otomatis.

    Tanpa env var guard tidak dipasang sama sekali — `docker compose` lokal, dev,
    dan seluruh test tetap polos seperti sebelumnya.
    """
    sandi = os.environ.get("STOKLENS_PASSWORD")
    if not sandi:
        return
    harapan = "Basic " + base64.b64encode(f"stoklens:{sandi}".encode()).decode()

    @app.middleware("http")
    async def guard(request, call_next):
        # compare_digest, bukan ==: mencegah penebakan sandi lewat selisih waktu.
        if not secrets.compare_digest(request.headers.get("authorization", ""), harapan):
            return Response(status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="StokLens"'})
        return await call_next(request)


def create_app(db_path=None, embedder=None, photo_detector=None):
    """photo_detector: fn(image_bgr)->boxes untuk mode foto; None = YOLO asli.

    db_path: None = ambil dari env `STOKLENS_DB`, jatuh ke `stoklens.db` di
    direktori kerja kalau env tidak ada. Env-nya dipakai `docker-compose.yml`
    untuk menaruh DB di volume (`/app/data`) — tanpa itu file DB tertulis di
    layer container dan hilang tiap `docker compose down`. Argumen eksplisit
    selalu menang atas env supaya test tidak bisa terganggu env mesin developer.
    """
    if db_path is None:
        db_path = os.environ.get("STOKLENS_DB", "stoklens.db")
    # Folder induk DB dibuat eksplisit: docker compose menunjuk /app/data yang
    # bisa saja belum ada, dan sqlite tidak membuat direktori sendiri — gagalnya
    # berupa "unable to open database file" saat request pertama, jauh dari
    # penyebabnya. `:memory:` dan nama file polos punya parent "." → dilewati.
    induk = Path(db_path).parent
    if str(induk) not in ("", "."):
        induk.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="StokLens")
    crops_prefix = crops.DIR_CROPS_DEFAULT.as_posix()

    # Setiap pemakaian con() WAJIB dibungkus contextlib.closing. Tanpa itu
    # koneksinya cuma menunggu garbage collector: CPython "biasanya" menutupnya,
    # tapi tidak dijamin, dan sementara itu file DB tetap tertahan (di Windows
    # sampai tidak bisa dihapus) sambil memakan file descriptor per request.
    #
    # Sengaja TIDAK memakai dependency FastAPI (`Depends`) walau itu pola yang
    # biasa: endpoint di sini `def` (sinkron), dan FastAPI menjalankan
    # dependency sinkron di worker threadpool yang BELUM TENTU thread yang sama
    # dengan yang menjalankan handler-nya. Dengan check_same_thread=True bawaan
    # sqlite3, koneksi yang lahir di dependency lalu dipakai di handler melempar
    # ProgrammingError begitu ada dua request bersamaan — dan tidak terlihat
    # sama sekali saat request datang satu-satu (anyio memakai ulang worker yang
    # menganggur, jadi kebetulan se-thread). Dijaga oleh
    # tests/test_api_koneksi.py::test_koneksi_aman_saat_request_bersamaan.
    def con():
        return db.connect(db_path)

    def get_embedder():
        nonlocal embedder
        if embedder is None:
            from .embedder import ClipEmbedder
            embedder = ClipEmbedder()
        return embedder

    _pasang_guard(app)
    app.include_router(webui_router)
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    # StaticFiles butuh direktori sudah ada saat mount — sengaja dibuat di sini
    # untuk SETIAP create_app(), bukan cuma yang perlu /crops. Efek samping ini
    # ditolerir (folder digitignore, "data/") demi tidak lazy-mount /crops.
    crops.DIR_CROPS_DEFAULT.mkdir(parents=True, exist_ok=True)
    app.mount("/crops", StaticFiles(directory=str(crops.DIR_CROPS_DEFAULT)), name="crops")

    # CATATAN PENTING untuk ketiga endpoint berat di bawah (enrollment, scan
    # video, scan foto): pipeline-nya sinkron dan berat (YOLO + CLIP + OCR).
    # Kerja itu WAJIB lewat run_in_threadpool — kalau dijalankan langsung di
    # dalam `async def`, ia menempati event loop dan SELURUH aplikasi beku
    # selama scan (halaman tidak bisa dibuka, tombol tidak merespons). Terukur:
    # GET /api/products tidak bisa mulai sampai scan selesai. Dijaga oleh
    # tests/test_api_concurrency.py.
    #
    # Koneksi SQLite dibuat DI DALAM fungsi thread, bukan di luar lalu dibawa
    # masuk: sqlite3.connect default check_same_thread=True, jadi koneksi milik
    # event loop yang dipakai di thread lain melempar ProgrammingError.

    @app.post("/products")
    async def create_product(nama: str = Form(...),
                             harga_modal: int = Form(..., ge=0),
                             qty_awal: int = Form(0, ge=0),
                             harga_jual: int = Form(None, ge=0),
                             stok_minimum: int = Form(0, ge=0),
                             fotos: list[UploadFile] = None):
        from .enroll import enroll_product
        # Tanpa guard ini `for f in fotos` melempar TypeError -> 500. UI sudah
        # mewajibkan minimal satu foto, tapi API tidak boleh bergantung ke UI.
        if not fotos:
            raise HTTPException(400, "Minimal satu foto barang diperlukan")
        # Baca isi upload di event loop (I/O, murah), sisanya di threadpool.
        isi = [(f.filename, await f.read()) for f in fotos]

        def kerja():
            tmp = Path(tempfile.mkdtemp())
            try:
                paths = []
                for nama_file, data in isi:
                    p = tmp / nama_file
                    p.write_bytes(data)
                    # Divalidasi di sini, bukan dibiarkan meledak di
                    # enroll_product -> Image.open: pesan 500 di sana tidak
                    # menyebut file mana yang rusak. Pola & pesan disamakan
                    # dengan /api/scans-foto yang sudah 400.
                    if not _gambar_valid(p):
                        raise HTTPException(
                            400, f"File bukan gambar valid: {nama_file}")
                    paths.append(p)
                with closing(con()) as c:
                    pid = enroll_product(c, get_embedder(), nama, harga_modal, paths,
                                         harga_jual=harga_jual, qty_awal=qty_awal)
                    if stok_minimum > 0:
                        db.update_product(c, pid, stok_minimum=stok_minimum)
                    return pid
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

        return {"product_id": await run_in_threadpool(kerja)}

    @app.post("/scans")
    async def create_scan(video: UploadFile, lokasi_rak: str = Form(None),
                          count_mode: str = Form("line")):
        from .scan import run_scan
        nama_file, data = video.filename, await video.read()

        def kerja():
            tmp = Path(tempfile.mkdtemp()) / nama_file
            tmp.write_bytes(data)
            with closing(con()) as c:
                return run_scan(c, get_embedder(), tmp, lokasi_rak=lokasi_rak,
                                count_mode=count_mode)

        return {"scan_id": await run_in_threadpool(kerja)}

    @app.get("/report/{scan_id}")
    def report(scan_id: int):
        with closing(con()) as c:
            scan = db.get_scan(c, scan_id)
            if scan is None:
                raise HTTPException(404, "Scan tidak ditemukan")
            # Key "scan" tambahan (additive) — konsumen lama yang cuma baca
            # items/total_* tetap aman.
            return build_report(
                db.get_report_rows(c, scan_id),
                tidak_terdeteksi=db.get_tidak_terdeteksi(c, scan_id)) | {
                    "scan": scan,
                }

    @app.post("/api/scans-foto")
    async def api_scan_foto(fotos: list[UploadFile], lokasi_rak: str = Form(None),
                            guided_product_id: int = Form(None),
                            read_expiry: bool = Form(False)):
        from .photo import scan_photos
        # Kedua batas dicek SEBELUM decode — lihat MAKS_* di atas. Jumlah dicek
        # duluan karena len(fotos) tersedia tanpa membaca satu byte pun. Catatan:
        # yang dihemat di sini biaya DECODE, bukan biaya terima — starlette sudah
        # men-spool seluruh body sebelum handler jalan (part di bawah 1 MB tetap
        # residen di RAM, selebihnya ke disk), jadi 30 part @900 KB sudah 26 MB
        # di memori saat baris ini dievaluasi. Batas body sungguhan tempatnya di
        # reverse-proxy, bukan di sini.
        if len(fotos) > MAKS_FOTO_PER_SCAN:
            raise HTTPException(
                400, f"Maksimal {MAKS_FOTO_PER_SCAN} foto per scan, "
                     f"dikirim {len(fotos)}")
        isi = []
        for f in fotos:
            # f.size sudah diisi parser multipart sebelum handler dipanggil, jadi
            # foto raksasa ditolak tanpa pernah ditarik utuh ke RAM oleh handler
            # (isinya sendiri sudah ter-spool, lihat catatan di atas). Tipenya boleh
            # None (UploadFile yang dirakit manual, bukan dari multipart), maka
            # len(data) tetap dicek sesudah read — kalau tidak, size=None jadi
            # lubang yang meloloskan file besar.
            if f.size is not None and f.size > MAKS_BYTE_PER_FOTO:
                raise _galat_foto_terlalu_besar(f.filename, f.size)
            data = await f.read()
            if len(data) > MAKS_BYTE_PER_FOTO:
                raise _galat_foto_terlalu_besar(f.filename, len(data))
            isi.append((f.filename, data))

        def kerja():
            import cv2
            import numpy as np
            # Decode ikut masuk threadpool: untuk foto 12 MP ini sendiri sudah
            # berat, dan HTTPException yang dilempar dari sini tetap ditangani
            # FastAPI seperti biasa.
            images = []
            for nama_file, data in isi:
                img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    raise HTTPException(400, f"File bukan gambar valid: {nama_file}")
                images.append(img)
            with closing(con()) as c:
                sid = scan_photos(c, get_embedder(), images, detector=photo_detector,
                                  guided_product_id=guided_product_id,
                                  lokasi_rak=lokasi_rak, read_expiry=read_expiry)
                return sid, build_report(
                    db.get_report_rows(c, sid),
                    tidak_terdeteksi=db.get_tidak_terdeteksi(c, sid))

        sid, rep = await run_in_threadpool(kerja)
        return {"scan_id": sid, "report": rep}

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
        with closing(con()) as c:
            stock = db.get_stock_map(c)
            return [_product_row(p, stock) for p in db.all_products(c)]

    @app.get("/api/products/{product_id}")
    def api_product_detail(product_id: int):
        with closing(con()) as c:
            p = db.get_product(c, product_id)
            if p is None:
                raise HTTPException(404, "Produk tidak ditemukan")
            p = _product_row(p, db.get_stock_map(c))
            p["ledger"] = db.get_ledger(c, product_id)
            return p

    @app.patch("/api/products/{product_id}")
    def api_product_patch(product_id: int, patch: ProductPatch):
        with closing(con()) as c:
            if db.get_product(c, product_id) is None:
                raise HTTPException(404, "Produk tidak ditemukan")
            fields = {k: v for k, v in patch.model_dump().items() if v is not None}
            try:
                db.update_product(c, product_id, **fields)
            except sqlite3.IntegrityError as e:
                # products.nama UNIQUE. Tanpa tangkapan ini user yang mengganti
                # nama jadi nama yang sudah dipakai cuma melihat error 500
                # generik. Pesannya disamakan dengan
                # /api/unknown/{crop_id}/produk-baru.
                raise HTTPException(
                    400, f"Nama produk '{fields.get('nama')}' sudah dipakai") from e
            return {"ok": True}

    @app.post("/api/adjustments")
    def api_adjustment(adj: Adjustment):
        with closing(con()) as c:
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
        with closing(con()) as c:
            # Validasi SEBELUM add_scan: request yang ditolak tidak boleh
            # meninggalkan baris scans/scan_items setengah jadi.
            if not body.items:
                raise HTTPException(400, "Opname harus berisi minimal satu barang")
            ids = [i.product_id for i in body.items]
            # Dobel ditolak, bukan digabung: menebak maksud user menyembunyikan
            # bug di sisi pemanggil. Dan kalau lolos, kedua baris masuk laporan
            # sehingga total_shrinkage_rp menghitung ganda.
            # Daftar id diurutkan supaya pesannya deterministik.
            dobel = sorted(i for i, n in Counter(ids).items() if n > 1)
            if dobel:
                raise HTTPException(
                    400, "product_id dobel dalam satu opname: "
                         + ", ".join(map(str, dobel)))
            # get_report_rows JOIN ke products, jadi id yang tidak ada terbuang
            # dari laporan tanpa pesan apa pun — user tidak tahu itemnya tidak
            # terhitung. Semua id diambil satu query, bukan get_product per item
            # (hindari N+1). Sumbernya WAJIB tabel products, bukan get_stock_map:
            # produk yang baru di-enroll belum punya baris stock_ledger dan tetap
            # sah untuk di-opname.
            dikenal = {p["id"] for p in db.all_products(c)}
            asing = sorted(set(ids) - dikenal)
            if asing:
                raise HTTPException(
                    400, "product_id tidak dikenal: " + ", ".join(map(str, asing)))
            scan_id = db.add_scan(c, lokasi_rak=body.lokasi_rak, tipe="manual")
            for item in body.items:
                db.add_scan_item(c, scan_id, item.product_id, item.qty_fisik)
            # Report WAJIB dihitung sebelum terapkan: qty_tercatat-nya diambil
            # dari ledger saat ini, kalau ledger ditulis duluan semua selisih
            # jadi 0.
            rep = build_report(db.get_report_rows(c, scan_id),
                               tidak_terdeteksi=db.get_tidak_terdeteksi(c, scan_id))
            if body.terapkan:
                db.terapkan_opname(c, scan_id)
            return {"scan_id": scan_id, "diterapkan": body.terapkan, "report": rep}

    @app.get("/api/scans")
    def api_scans():
        with closing(con()) as c:
            scans = db.list_scans(c)
            # Satu query untuk semua scan (bukan get_report_rows per-scan di
            # loop) — jumlah query jadi konstan, tidak tumbuh mengikuti jumlah
            # scan.
            rows_per_scan = db.get_report_rows_by_scan(c)
            out = []
            for s in scans:
                rep = build_report(rows_per_scan.get(s["id"], []))
                out.append(s | {
                    "total_shrinkage_rp": rep["total_shrinkage_rp"],
                    "total_rugi_expired_rp": rep["total_rugi_expired_rp"],
                })
            return out

    @app.post("/api/opname/{scan_id}/terapkan")
    def api_opname_terapkan(scan_id: int):
        with closing(con()) as c:
            scan = db.get_scan(c, scan_id)
            if scan is None:
                raise HTTPException(404, "Scan tidak ditemukan")
            # Guard terapkan ganda: snapshot lama tidak boleh menimpa stok
            # sekarang.
            if scan["terapkan_pada"] is not None:
                raise HTTPException(409, "Opname ini sudah diterapkan")
            try:
                jumlah = db.terapkan_opname(c, scan_id)
            except db.OpnameSudahDiterapkan as e:
                # Cek di atas cuma untuk pesan; guard sebenarnya ada di helper
                # (compare-and-set). Sampai sini artinya request lain menang
                # balapan setelah cek — jawabannya 409, bukan 500. Catatan: kalau
                # dua penulis benar-benar tumpang tindih, SQLite bisa lebih dulu
                # melempar "database is locked" dan itu tetap jadi 500.
                raise HTTPException(409, "Opname ini sudah diterapkan") from e
            return {"ok": True, "jumlah_item": jumlah}

    @app.get("/api/dashboard")
    def api_dashboard():
        with closing(con()) as c:
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
        # Seluruh CSV dirakit di StringIO SEBELUM response dibuat, jadi koneksi
        # boleh ditutup di sini. Kalau kelak diubah jadi StreamingResponse yang
        # menghasilkan baris sambil dikirim, koneksinya sudah tertutup saat
        # generator jalan — pindahkan penutupannya ke akhir generator.
        with closing(con()) as c:
            stock = db.get_stock_map(c)
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["id", "nama", "qty", "harga_modal", "harga_jual",
                        "margin_pct", "nilai_stok_rp"])
            for p in db.all_products(c):
                qty = stock.get(p["id"], 0)
                w.writerow([p["id"], p["nama"], qty, p["harga_modal"],
                            p["harga_jual"] or "",
                            accounting.margin_pct(p["harga_modal"],
                                                  p["harga_jual"]) or "",
                            qty * p["harga_modal"]])
        return PlainTextResponse(
            buf.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=stok.csv"})

    # ---------- Unknown crops (enroll dari scan) ----------
    # PENTING: endpoint di bawah TIDAK BOLEH memanggil get_embedder() — embedding
    # sudah tersimpan di baris unknown_crops (Unit 1&2), jadi tidak perlu CLIP.

    @app.get("/api/scans/{scan_id}/unknown")
    def api_scan_unknown(scan_id: int):
        with closing(con()) as c:
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
        with closing(con()) as c:
            crop = db.get_unknown_crop(c, crop_id)
            if crop is None:
                raise HTTPException(404, "Crop tidak ditemukan")
            if db.get_product(c, body.product_id) is None:
                raise HTTPException(404, "Produk tidak ditemukan")
            if crop["product_id"] is not None:
                raise HTTPException(409, "Crop ini sudah di-resolve")
            db.add_product_embedding(c, body.product_id, crop["embedding"],
                                     sumber="scan")
            hasil = penamaan.selesaikan_penamaan(c, crop_id, body.product_id)
            return {
                "ok": True,
                "product_id": body.product_id,
                "jumlah_galeri": db.count_product_embeddings(c, body.product_id),
                "dipindah": hasil["dipindah"],
                "ikut_terbawa": hasil["ikut_terbawa"],
            }

    @app.post("/api/unknown/{crop_id}/produk-baru")
    def api_unknown_produk_baru(crop_id: int, body: UnknownProdukBaru):
        with closing(con()) as c:
            crop = db.get_unknown_crop(c, crop_id)
            if crop is None:
                raise HTTPException(404, "Crop tidak ditemukan")
            if crop["product_id"] is not None:
                raise HTTPException(409, "Crop ini sudah di-resolve")
            try:
                pid = db.add_product(c, body.nama, body.harga_modal,
                                     crop["embedding"], harga_jual=body.harga_jual)
            except sqlite3.IntegrityError as e:
                raise HTTPException(
                    400, f"Nama produk '{body.nama}' sudah dipakai") from e
            if body.qty_awal:
                db.set_stock(c, pid, body.qty_awal)
            if body.stok_minimum > 0:
                db.update_product(c, pid, stok_minimum=body.stok_minimum)
            hasil = penamaan.selesaikan_penamaan(c, crop_id, pid)
            return {
                "ok": True,
                "product_id": pid,
                "dipindah": hasil["dipindah"],
                "ikut_terbawa": hasil["ikut_terbawa"],
            }

    @app.get("/")
    def root():
        return RedirectResponse(url="/ui/beranda")

    return app
