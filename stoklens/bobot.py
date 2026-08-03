"""Pemilihan bobot detektor — satu tempat, dan berisik kalau salah.

MASALAH YANG DITUTUP
--------------------
Bobot bawaan `yolo11n.pt` adalah model COCO (orang/mobil/anjing). Diukur pada
foto rak warung asli ia memberi **0 kotak**. README sudah menuliskannya, tapi
saat dijalankan aplikasinya DIAM: orang menjalankan `docker compose up`, scan
sebuah foto, dapat nol hasil, dan tidak ada satu pun petunjuk kenapa.

Bagi juri yang menjalankan sekali tanpa membaca README, itu terbaca sebagai
aplikasi rusak. Modul ini membuat keadaan itu mengumumkan dirinya sendiri — di
log saat model dimuat, dan lewat spanduk di UI.

Sengaja memeriksa KONFIGURASI, bukan isi model. Kasus nyatanya adalah
`STOKLENS_MODEL` tidak diset sama sekali; memuat model hanya untuk mengintip
nama kelasnya berarti membayar ratusan MB untuk menjawab pertanyaan yang sudah
terjawab oleh ketiadaan env itu sendiri. Bobot yang diset tapi jalurnya salah
akan gagal dengan galat yang jelas dari ultralytics — itu bukan kegagalan diam.
"""
import logging
import os

BOBOT_DEFAULT = "yolo11n.pt"
ENV_BOBOT = "STOKLENS_MODEL"

_log = logging.getLogger(__name__)
_sudah_diperingatkan = False

PESAN_SINGKAT = "Detektor memakai bobot COCO bawaan — scan foto akan memberi 0 hasil."
PESAN_PANJANG = (
    f"{PESAN_SINGKAT} Arahkan env {ENV_BOBOT} ke bobot hasil pre-train/fine-tune. "
    'Lihat README §"Menukar bobot detektor".'
)


def jalur_bobot(model_path=None):
    """Jalur bobot yang benar-benar dipakai. Argumen eksplisit menang atas env."""
    return model_path or os.environ.get(ENV_BOBOT, BOBOT_DEFAULT)


def pakai_bobot_bawaan(model_path=None):
    """True kalau yang dipakai bobot COCO bawaan — artinya scan tidak akan menemukan apa pun."""
    return jalur_bobot(model_path) == BOBOT_DEFAULT


def muat_yolo(model_path=None):
    """Muat YOLO, dan peringatkan sekali kalau bobotnya bawaan.

    Diperingatkan sekali per proses saja: pemuatan terjadi tiap scan, dan log
    yang mengulang pesan sama tiap permintaan justru membuatnya terabaikan.
    """
    global _sudah_diperingatkan
    jalur = jalur_bobot(model_path)
    if pakai_bobot_bawaan(model_path) and not _sudah_diperingatkan:
        _sudah_diperingatkan = True
        _log.warning("=" * 70)
        _log.warning(PESAN_PANJANG)
        _log.warning("=" * 70)

    from ultralytics import YOLO
    return YOLO(jalur)
