import pytest

from stoklens.accounting import (
    apply_adjustment,
    margin_pct,
    nilai_stok,
    potensi_laba,
    stok_menipis,
)


def _products():
    return [
        {"id": 1, "nama": "Indomie", "harga_modal": 3200, "harga_jual": 3500,
         "stok_minimum": 10},
        {"id": 2, "nama": "Minyak", "harga_modal": 15000, "harga_jual": None,
         "stok_minimum": 0},
    ]


def test_margin_pct():
    assert margin_pct(3200, 3500) == 9.4


def test_margin_pct_tanpa_harga_jual():
    assert margin_pct(3200, None) is None


def test_margin_pct_modal_nol():
    assert margin_pct(0, 3500) is None


def test_nilai_stok_pakai_harga_modal():
    assert nilai_stok(_products(), {1: 40, 2: 10}) == 40 * 3200 + 10 * 15000


def test_nilai_stok_produk_tanpa_ledger_dihitung_nol():
    assert nilai_stok(_products(), {}) == 0


def test_potensi_laba_hanya_produk_dengan_harga_jual():
    # Minyak tanpa harga_jual tidak menyumbang laba
    assert potensi_laba(_products(), {1: 40, 2: 10}) == 40 * (3500 - 3200)


def test_stok_menipis_hanya_yang_punya_minimum():
    tipis = stok_menipis(_products(), {1: 9, 2: 0})
    assert [p["id"] for p in tipis] == [1]
    assert tipis[0]["qty"] == 9


def test_stok_di_atas_minimum_tidak_masuk():
    assert stok_menipis(_products(), {1: 11, 2: 5}) == []


def test_apply_adjustment():
    assert apply_adjustment(10, -3) == 7


def test_apply_adjustment_tidak_boleh_negatif():
    with pytest.raises(ValueError):
        apply_adjustment(2, -5)
