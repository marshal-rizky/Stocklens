"""Enrollment: foto barang -> rata-rata embedding -> DB."""
from PIL import Image

from . import db
from .matcher import average_embedding


def enroll_product(con, embedder, nama, harga_modal, foto_paths,
                   harga_jual=None, qty_awal=0):
    """Daftarkan produk dari 1+ foto; return product_id."""
    vecs = [embedder.embed_pil(Image.open(p).convert("RGB")) for p in foto_paths]
    pid = db.add_product(
        con, nama, harga_modal, average_embedding(vecs),
        harga_jual=harga_jual, foto_refs=[str(p) for p in foto_paths],
    )
    if qty_awal:
        db.set_stock(con, pid, qty_awal)
    return pid
