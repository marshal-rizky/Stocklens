"""Wrapper CLIP (open_clip) untuk embedding gambar produk."""
import cv2
import numpy as np
import torch
import open_clip
from PIL import Image


class ClipEmbedder:
    def __init__(self, model_name="ViT-B-32", pretrained="laion2b_s34b_b79k", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self.model.eval().to(self.device)

    @torch.no_grad()
    def embed_pil(self, img: Image.Image) -> np.ndarray:
        x = self.preprocess(img).unsqueeze(0).to(self.device)
        v = self.model.encode_image(x)[0].cpu().numpy().astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-9)

    def embed_bgr(self, arr: np.ndarray) -> np.ndarray:
        return self.embed_pil(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)))


# Re-export untuk kompatibilitas (implementasi pindah ke matcher.py yang bebas torch)
from .matcher import average_embedding  # noqa: E402,F401
