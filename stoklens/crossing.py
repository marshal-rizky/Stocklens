"""Line-crossing counting: anti dobel hitung untuk rekaman sweep.

MASALAH YANG DISELESAIKAN
-------------------------
Hitungan berbasis track ID bisa dobel kalau ID pecah (barang sama dapat 2 ID
karena blur/ketutupan/kamera goyang). Solusi: track hanya dihitung saat
MELINTASI garis virtual di tengah layar, searah gerakan sweep.

Kenapa ini ampuh:
- ID pecah di sisi layar yang sama -> hanya satu ID yang sempat menyeberang
  garis -> tetap dihitung 1.
- Kamera goyang maju-mundur kecil -> diserap hysteresis (zona mati di sekitar
  garis), tidak menghasilkan event.
- Barang menyeberang balik (kamera mundur jauh) -> event -1, saling menghapus
  dengan +1 sebelumnya -> self-correcting.

KAPAN DIPAKAI
-------------
Hanya untuk rekaman SWEEP (kamera bergerak satu arah menyusuri rak).
Untuk kamera statis barang tidak pernah menyeberang garis -> hitungan 0;
pakai mode "track" biasa di scan.run_scan(count_mode="track").

Semua posisi x dinormalisasi 0..1 (center bounding box / lebar frame).
"""


def crossing_events(xs, line=0.5, hysteresis=0.05):
    """Deteksi event menyeberang garis dari deret posisi center-x satu track.

    Hysteresis: track harus benar-benar keluar dari zona [line-h, line+h]
    sebelum dianggap pindah sisi — jitter kecil di sekitar garis diabaikan.

    Return list arah event, urut waktu: +1 (kiri->kanan), -1 (kanan->kiri).
    """
    lo, hi = line - hysteresis, line + hysteresis
    events = []
    side = None  # sisi terakhir yang JELAS: "L" atau "R"; None = belum jelas
    for x in xs:
        if x < lo:
            if side == "R":
                events.append(-1)
            side = "L"
        elif x > hi:
            if side == "L":
                events.append(1)
            side = "R"
        # x di dalam zona hysteresis: sisi tidak berubah
    return events


def net_crossing(xs, line=0.5, hysteresis=0.05):
    """Jumlah bersih penyeberangan (event saling menghapus). 1 barang normal = 1."""
    return sum(crossing_events(xs, line, hysteresis))


def count_by_crossing(track_xs, line=0.5, hysteresis=0.05):
    """Tentukan track mana yang dihitung, berdasarkan penyeberangan garis.

    track_xs: {track_id: [center_x ternormalisasi, urut waktu]}

    Arah sweep TIDAK perlu dideklarasikan user — ditentukan otomatis dari
    mayoritas arah penyeberangan semua track (asumsi: sebagian besar track
    adalah barang asli yang mengalir searah sweep).

    Return ({track_id: bool_dihitung}, arah_sweep) dengan arah +1 = kiri->kanan.
    """
    nets = {tid: net_crossing(xs, line, hysteresis) for tid, xs in track_xs.items()}
    direction = 1 if sum(nets.values()) >= 0 else -1
    counted = {tid: (n * direction) >= 1 for tid, n in nets.items()}
    return counted, direction
