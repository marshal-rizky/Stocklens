"""Bobot bawaan harus mengumumkan dirinya, bukan gagal diam-diam.

Bobot `yolo11n.pt` adalah model COCO dan memberi 0 kotak di foto rak warung.
Sebelum ini aplikasinya diam: orang menjalankan `docker compose up`, scan, dapat
nol hasil, dan mengira aplikasinya rusak. Test ini menjaga peringatannya tetap
ada — di log maupun di UI.
"""
import logging

from fastapi.testclient import TestClient

from stoklens import bobot
from stoklens.api import create_app


def _client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "t.db")))


def test_tanpa_env_dianggap_bobot_bawaan(monkeypatch):
    monkeypatch.delenv(bobot.ENV_BOBOT, raising=False)
    assert bobot.pakai_bobot_bawaan() is True
    assert bobot.jalur_bobot() == bobot.BOBOT_DEFAULT


def test_env_terisi_bukan_bobot_bawaan(monkeypatch):
    monkeypatch.setenv(bobot.ENV_BOBOT, "/bobot/best.pt")
    assert bobot.pakai_bobot_bawaan() is False
    assert bobot.jalur_bobot() == "/bobot/best.pt"


def test_argumen_eksplisit_menang_atas_env(monkeypatch):
    """Sama seperti db_path di api.py — argumen selalu mengalahkan env."""
    monkeypatch.setenv(bobot.ENV_BOBOT, "/bobot/dari-env.pt")
    assert bobot.jalur_bobot("/bobot/eksplisit.pt") == "/bobot/eksplisit.pt"
    assert bobot.pakai_bobot_bawaan("/bobot/eksplisit.pt") is False
    assert bobot.pakai_bobot_bawaan(bobot.BOBOT_DEFAULT) is True


def test_spanduk_tampil_di_semua_halaman_saat_bobot_bawaan(tmp_path, monkeypatch):
    monkeypatch.delenv(bobot.ENV_BOBOT, raising=False)
    client = _client(tmp_path)
    for path in ("/ui/beranda", "/ui/barang", "/ui/opname", "/ui/opname/foto",
                 "/ui/laporan"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "spanduk-bobot" in r.text, f"spanduk hilang di {path}"
        assert "STOKLENS_MODEL" in r.text, path


def test_spanduk_hilang_saat_bobot_diarahkan(tmp_path, monkeypatch):
    monkeypatch.setenv(bobot.ENV_BOBOT, "/bobot/best.pt")
    r = _client(tmp_path).get("/ui/beranda")
    assert r.status_code == 200
    assert "spanduk-bobot" not in r.text


def test_peringatan_log_muncul_sekali(monkeypatch, caplog):
    """Pemuatan terjadi tiap scan; log yang mengulang tiap permintaan jadi diabaikan."""
    monkeypatch.delenv(bobot.ENV_BOBOT, raising=False)
    monkeypatch.setattr(bobot, "_sudah_diperingatkan", False)

    # Yang diuji peringatannya, bukan pemuatan modelnya. Kegagalan sesudah
    # peringatan ditelan apa pun bentuknya: di CI ultralytics tidak terpasang
    # (ImportError), di mesin dev ia terpasang dan jalurnya yang tidak ada
    # (FileNotFoundError). Menebak salah satunya membuat test hijau di satu
    # tempat dan merah di tempat lain.
    for _ in range(3):
        with caplog.at_level(logging.WARNING, logger="stoklens.bobot"):
            try:
                bobot.muat_yolo()
            except Exception:
                pass

    peringatan = [r for r in caplog.records if bobot.PESAN_SINGKAT in r.message]
    assert len(peringatan) == 1, f"harus sekali, dapat {len(peringatan)}"


def test_muat_yolo_diam_saat_bobot_diarahkan(monkeypatch, caplog):
    monkeypatch.setenv(bobot.ENV_BOBOT, "/bobot/best.pt")
    monkeypatch.setattr(bobot, "_sudah_diperingatkan", False)
    with caplog.at_level(logging.WARNING, logger="stoklens.bobot"):
        try:
            bobot.muat_yolo()
        except Exception:      # sama alasannya seperti test di atas
            pass
    assert not [r for r in caplog.records if bobot.PESAN_SINGKAT in r.message]
