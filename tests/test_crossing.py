from stoklens.crossing import count_by_crossing, crossing_events, net_crossing


def test_nyebrang_sekali_kiri_ke_kanan():
    # barang "mengalir" melewati garis tengah saat kamera sweep
    assert crossing_events([0.2, 0.4, 0.6, 0.8]) == [1]


def test_jitter_di_sekitar_garis_tidak_dihitung():
    # goyangan kecil di sekitar garis 0.5 diserap hysteresis
    assert crossing_events([0.48, 0.52, 0.49, 0.51, 0.50]) == []


def test_bolak_balik_saling_menghapus():
    # kamera mundur: nyebrang balik jadi -1, net kembali 0
    xs = [0.2, 0.7, 0.2]
    assert crossing_events(xs) == [1, -1]
    assert net_crossing(xs) == 0


def test_mundur_lalu_maju_lagi_tetap_satu():
    # jitter besar: +1 -1 +1 = net 1, barang tetap dihitung sekali
    assert net_crossing([0.2, 0.7, 0.3, 0.8]) == 1


def test_count_by_crossing_arah_dominan():
    track_xs = {
        1: [0.2, 0.5, 0.8],        # nyebrang searah sweep
        2: [0.1, 0.6, 0.9],        # nyebrang searah sweep
        3: [0.6, 0.62, 0.61],      # diam di satu sisi (ID pecah) -> tidak dihitung
    }
    counted, direction = count_by_crossing(track_xs)
    assert direction == 1
    assert counted == {1: True, 2: True, 3: False}


def test_count_by_crossing_sweep_kanan_ke_kiri():
    track_xs = {1: [0.9, 0.5, 0.1], 2: [0.8, 0.4, 0.2]}
    counted, direction = count_by_crossing(track_xs)
    assert direction == -1
    assert counted == {1: True, 2: True}
