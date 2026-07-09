import pytest
from PIL import Image


@pytest.mark.slow
def test_enroll_masuk_db(tmp_path):
    from stoklens import db
    from stoklens.embedder import ClipEmbedder
    from stoklens.enroll import enroll_product
    foto = tmp_path / "indomie.jpg"
    Image.new("RGB", (128, 128), (220, 40, 40)).save(foto)
    con = db.connect(":memory:")
    pid = enroll_product(con, ClipEmbedder(), "Indomie Goreng", 3200, [foto], qty_awal=40)
    prods = db.all_products(con)
    assert prods[0]["id"] == pid and prods[0]["embedding"].shape == (512,)
    assert db.get_stock_map(con) == {pid: 40}
