import numpy as np
import pytest
from PIL import Image


@pytest.mark.slow
def test_embedding_normalized_dan_konsisten():
    from stoklens.embedder import ClipEmbedder, average_embedding
    e = ClipEmbedder()
    img = Image.new("RGB", (64, 64), (200, 30, 30))
    v1, v2 = e.embed_pil(img), e.embed_pil(img)
    assert abs(np.linalg.norm(v1) - 1.0) < 1e-3
    assert float(np.dot(v1, v2)) > 0.999
    assert abs(np.linalg.norm(average_embedding([v1, v2])) - 1.0) < 1e-3
