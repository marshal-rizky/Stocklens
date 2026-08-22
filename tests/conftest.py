"""Penjaga bersama untuk seluruh suite."""
import pytest


@pytest.fixture(autouse=True)
def _tanpa_sandi_guard(monkeypatch):
    """Buang STOKLENS_PASSWORD dari environment di setiap test.

    Guard HTTP Basic aktif kalau env var itu ada. Siapa pun yang memakai
    `scripts/jalan_hybrid.ps1` WAJIB menyetelnya secara permanen (`setx`), jadi
    justru orang yang menjalankan tunnel akan melihat ratusan test gagal dengan
    401 — dan CI tidak pernah menangkapnya, karena runner tidak punya env var itu.
    Terukur sekali: 108 dari 227 test gagal di mesin yang tunnel-nya menyala.

    Test yang memang ingin menguji guard menyalakannya sendiri lewat
    `monkeypatch.setenv`, yang dijalankan setelah fixture ini.
    """
    monkeypatch.delenv("STOKLENS_PASSWORD", raising=False)
