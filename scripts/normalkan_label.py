"""Ubah label poligon jadi kotak di export YOLO, sebelum dipakai training.

KENAPA INI HARUS ADA
--------------------
Roboflow Smart Polygon boleh dipakai — di sisi Roboflow poligon memang
dikonversi jadi bounding box. Tapi ekspor format YOLO menulis koordinat
poligonnya apa adanya: baris poligon jadi `cls x1 y1 x2 y2 ... xn yn`,
sementara baris kotak tetap `cls cx cy w h`.

Ultralytics lalu membacanya begini (ultralytics/data/utils.py):

    if any(len(x) > 6 for x in lb) and (not keypoint):   # is segment
        segments = [np.array(x[1:]).reshape(-1, 2) for x in lb]
        lb = np.concatenate((classes.reshape(-1, 1), segments2boxes(segments)), 1)

Perhatikan `any(...)`: pemeriksaannya PER FILE, bukan per baris. Satu baris
poligon membuat SELURUH baris di file itu masuk jalur segmen. Baris kotak
`cls cx cy w h` di-reshape(-1, 2) jadi dua "titik" — (cx, cy) dan (w, h) —
lalu min/max-nya diambil sebagai sudut kotak. Titik pusat dan ukuran
diperlakukan sebagai dua koordinat sudut. Hasilnya kotak yang tidak
berhubungan dengan barang aslinya.

Tidak ada error. Training selesai normal, kurva terbentuk, metrik keluar, dan
modelnya diam-diam belajar dari kotak sampah. Di Roboflow labeler tetap melihat
poligon yang rapi — kerusakannya cuma ada di file .txt hasil ekspor.

Hanya file CAMPURAN yang rusak. Semua-kotak aman (jalur normal), semua-poligon
aman (semua benar dikonversi). Yang mematikan adalah kebiasaan wajar: poligon
untuk kerupuk gantung, kotak untuk dus — dalam satu foto.

Diukur pada gabungan export 22 Agustus 2026: 11.730 anotasi, 3.750 poligon
(32%) tersebar di 158 file; 2.339 baris kotak (20% dari seluruh anotasi)
berada di file campuran dan akan rusak.

Pakai (dari akar repo):
    python -m scripts.normalkan_label --sumber "datasets/export-roboflow"
    python -m scripts.normalkan_label --sumber "datasets/export-roboflow" --tulis

Tanpa `--tulis` hanya melaporkan, dan itu memang bawaannya.
"""
import argparse
import pathlib


def poligon_ke_kotak(baris: str) -> str:
    """Satu baris label YOLO -> bentuk kotak `cls cx cy w h`.

    Baris yang sudah 5 kolom dikembalikan apa adanya. Baris poligon diambil
    min/max x dan y-nya, persis seperti yang dilakukan Roboflow saat mengonversi
    poligon jadi bounding box.
    """
    p = baris.split()
    if len(p) == 5:
        return " ".join(p)
    xy = [float(v) for v in p[1:]]
    xs, ys = xy[0::2], xy[1::2]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    return f"{p[0]} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"


def periksa_berkas(teks: str) -> tuple[int, int, bool]:
    """Return (jumlah kotak, jumlah poligon, apakah campuran)."""
    kotak = poligon = 0
    for baris in teks.splitlines():
        p = baris.split()
        if not p:
            continue
        if len(p) == 5:
            kotak += 1
        else:
            poligon += 1
    return kotak, poligon, bool(kotak and poligon)


def normalkan(teks: str) -> str:
    hasil = [poligon_ke_kotak(b) for b in teks.splitlines() if b.split()]
    return "\n".join(hasil) + ("\n" if hasil else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sumber", required=True, help="folder export YOLO (dicari rekursif)")
    ap.add_argument("--tulis", action="store_true",
                    help="benar-benar tulis ulang label. Tanpa ini hanya melaporkan.")
    a = ap.parse_args()

    berkas = sorted(pathlib.Path(a.sumber).rglob("labels/*.txt"))
    if not berkas:
        raise SystemExit(f"tidak ada labels/*.txt di bawah {a.sumber}")

    n_kotak = n_poligon = n_campur = n_rusak = 0
    diubah = []
    for f in berkas:
        teks = f.read_text(encoding="utf-8")
        kotak, poligon, campur = periksa_berkas(teks)
        n_kotak += kotak
        n_poligon += poligon
        if campur:
            n_campur += 1
            n_rusak += kotak      # baris kotak inilah yang jadi sampah
        if poligon:
            diubah.append((f, normalkan(teks)))

    total = n_kotak + n_poligon
    print(f"{len(berkas)} berkas label, {total} anotasi")
    print(f"  kotak                : {n_kotak}")
    print(f"  poligon              : {n_poligon}"
          f" ({n_poligon / total * 100:.1f}%)" if total else "")
    print(f"  berkas campuran      : {n_campur}")
    print(f"  kotak yang AKAN RUSAK: {n_rusak}"
          f" ({n_rusak / total * 100:.1f}% dari seluruh anotasi)" if total else "")

    if not diubah:
        print("\nTidak ada poligon. Aman untuk training.")
        return
    if not a.tulis:
        print(f"\n{len(diubah)} berkas perlu dinormalkan. "
              "Jalankan ulang dengan --tulis untuk menerapkan.")
        return
    for f, teks in diubah:
        f.write_text(teks, encoding="utf-8")
    print(f"\n{len(diubah)} berkas ditulis ulang. Semua label kini 5 kolom.")


if __name__ == "__main__":
    main()
