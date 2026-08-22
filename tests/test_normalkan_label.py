"""Normalisasi label poligon -> kotak sebelum training.

Menguji juga perilaku yang membuat bug-nya berbahaya: ultralytics memakai
aturan `any(len(x) > 6)` PER FILE, jadi satu baris poligon merusak seluruh
baris kotak di file yang sama. Uji terakhir mereproduksi transformasi itu
tanpa mengimpor ultralytics, supaya suite cepat tetap bebas torch.
"""
from scripts.normalkan_label import normalkan, periksa_berkas, poligon_ke_kotak


def test_baris_kotak_lewat_apa_adanya():
    assert poligon_ke_kotak("0 0.5 0.5 0.2 0.4") == "0 0.5 0.5 0.2 0.4"


def test_poligon_jadi_kotak_pembungkusnya():
    # Segitiga dengan x 0,2-0,6 dan y 0,1-0,5 -> pusat (0,4 ; 0,3), lebar 0,4, tinggi 0,4
    hasil = poligon_ke_kotak("0 0.2 0.1 0.6 0.1 0.4 0.5")
    kelas, cx, cy, w, h = hasil.split()
    assert kelas == "0"
    assert (float(cx), float(cy)) == (0.4, 0.3)
    assert (round(float(w), 6), round(float(h), 6)) == (0.4, 0.4)


def test_periksa_menandai_berkas_campuran():
    campur = "0 0.5 0.5 0.2 0.2\n0 0.1 0.1 0.3 0.1 0.2 0.4\n"
    assert periksa_berkas(campur) == (1, 1, True)
    assert periksa_berkas("0 0.5 0.5 0.2 0.2\n")[2] is False
    assert periksa_berkas("0 0.1 0.1 0.3 0.1 0.2 0.4\n")[2] is False


def test_normalkan_menghasilkan_semua_lima_kolom():
    campur = "0 0.5 0.5 0.2 0.2\n0 0.1 0.1 0.3 0.1 0.2 0.4\n\n"
    hasil = normalkan(campur)
    baris = [b for b in hasil.splitlines() if b.strip()]
    assert len(baris) == 2
    assert all(len(b.split()) == 5 for b in baris)
    # Setelah normalisasi tidak ada lagi baris > 6 kolom, jadi cabang segmen
    # di ultralytics tidak pernah aktif.
    assert not any(len(b.split()) > 6 for b in baris)


def test_tanpa_normalisasi_baris_kotak_jadi_kotak_sampah():
    """Reproduksi jalur segmen ultralytics pada berkas campuran.

    `x[1:]` di-reshape jadi pasangan (x, y) lalu diambil min/max-nya. Untuk baris
    kotak, "titik"-nya adalah (cx, cy) dan (w, h) — pusat dan ukuran diperlakukan
    sebagai dua sudut. Uji ini mengunci fakta itu supaya alasan keberadaan
    normalisasi tidak hilang kalau ada yang menganggapnya berlebihan.
    """
    def jalur_segmen(baris):
        v = [float(x) for x in baris.split()[1:]]
        titik = list(zip(v[0::2], v[1::2]))
        xs = [t[0] for t in titik]
        ys = [t[1] for t in titik]
        return min(xs), min(ys), max(xs), max(ys)

    # Kotak di tengah frame, kecil.
    benar = (0.5, 0.5, 0.2, 0.2)          # cx, cy, w, h
    x1, y1, x2, y2 = jalur_segmen("0 0.5 0.5 0.2 0.2")
    rusak_cx, rusak_cy = (x1 + x2) / 2, (y1 + y2) / 2
    rusak_w, rusak_h = x2 - x1, y2 - y1

    assert (rusak_cx, rusak_cy, rusak_w, rusak_h) != benar
    # Konkretnya: titiknya jadi (0,5 ; 0,5) dan (0,2 ; 0,2), sehingga kotaknya
    # membentang dari 0,2 ke 0,5 di kedua sumbu — bukan kotak 0,2 x 0,2 di tengah.
    assert (round(rusak_w, 6), round(rusak_h, 6)) == (0.3, 0.3)
    assert (round(rusak_cx, 6), round(rusak_cy, 6)) == (0.35, 0.35)
