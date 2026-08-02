"""Pemilihan test set — SATU sumber kebenaran, dipakai bersama.

KENAPA MODUL SENDIRI
--------------------
Dua skrip butuh daftar foto uji yang sama persis:

  - `baseline_detektor.py` merekam perilaku "sebelum" di foto-foto itu
  - `kirim_roboflow.py` harus menaruh foto-foto itu di split `test`, supaya
    Roboflow tidak mengacaknya masuk ke training

Kalau keduanya punya salinan logika sendiri lalu salah satunya berubah, angka
"sebelum" dan "sesudah" diukur di kumpulan foto yang berbeda — dan tidak ada
yang gagal, hasilnya cuma bohong. Itu jenis kerusakan yang paling mahal karena
baru ketahuan setelah semuanya selesai. Jadi logikanya tinggal di sini saja.

CARA PEMILIHAN
--------------
Deterministik dan direproduksi dari triase, BUKAN dibaca dari Drive: satu dari
tiap empat foto rak, diurutkan per domain lalu per nama. Daftarnya sama persis
kapan pun dijalankan, bahkan kalau folder Drive berubah.

Pakai sebagai CLI untuk mengeluarkan daftarnya (satu baris = satu nama berkas):
    python -m scripts.testset --triase triase.json --triase-baru triase_baru.json --keluar daftar-uji.txt
"""
import argparse
import json
from collections import defaultdict

PORSI_UJI = 4          # 1 dari tiap 4 foto rak disisihkan
BUCKET_RAK = "1-DETEKTOR-foto-rak"
DOMAIN_LAMA = {"etalase": "warung", "closeup": "warung", "closeup-tablet": "minimarket"}


def domain(x):
    if "kategori" in x:
        return DOMAIN_LAMA.get(x["kategori"], "warung")
    return "warung" if "More useless" in x["path"] else "minimarket"


def pilih_uji(semua):
    rak = sorted([x for x in semua if x["bucket"] == BUCKET_RAK],
                 key=lambda x: (domain(x), x["nama"]))
    per = defaultdict(list)
    for x in rak:
        per[domain(x)].append(x)
    return [x for xs in per.values() for i, x in enumerate(xs) if i % PORSI_UJI == 0]


def muat_triase(jalur, jalur_baru=None):
    semua = json.load(open(jalur, encoding="utf-8"))
    if jalur_baru:
        semua += json.load(open(jalur_baru, encoding="utf-8"))
    return semua


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triase", required=True)
    ap.add_argument("--triase-baru")
    ap.add_argument("--keluar", default="daftar-uji.txt")
    a = ap.parse_args()

    uji = pilih_uji(muat_triase(a.triase, a.triase_baru))
    # Ditulis sebagai nama berkas UTUH (`<id>__<nama>`), bukan `<nama>` saja.
    # Nama asli dari HP bisa bertabrakan — di 171 foto rak ada 2 pasang yang
    # sama persis. Kalau yang ditulis cuma `<nama>`, satu foto latih ikut
    # tertarik ke split test hanya karena namanya kembar.
    with open(a.keluar, "w", encoding="utf-8") as fh:
        for x in sorted(uji, key=lambda x: (x["nama"], x["id"])):
            fh.write(f"{x['id']}__{x['nama']}\n")

    per = defaultdict(int)
    for x in uji:
        per[domain(x)] += 1
    print(f"{len(uji)} foto uji -> {a.keluar}")
    for d, n in sorted(per.items()):
        print(f"  {d:12s} {n}")
    print("\nFoto-foto ini WAJIB masuk split `test` waktu diunggah ke Roboflow.")
    print("Kalau ikut terlatih, perbandingan sebelum/sesudah jadi tidak sah.")


if __name__ == "__main__":
    main()
