"""Pipa dataset: dari foto mentah sampai siap-review di Roboflow, satu perintah.

Merangkai empat langkah yang sudah ada, dalam urutan yang benar, dengan penjaga
yang gampang terlupa kalau dijalankan satu-satu:

  1. scripts.testset          -> daftar foto uji (dikunci, jangan ikut dilatih)
  2. scripts.autolabel_grounding -> kotak awal dari detektor berbasis teks
  3. scripts.lembar_kontak    -> lembar kontak untuk triase mata manusia
  4. scripts.kirim_roboflow   -> unggah dengan split train/test yang benar

KENAPA DIRANGKAI
----------------
Dijalankan terpisah, langkah 1 dan flag `--daftar-uji` di langkah 4 paling
gampang terlewat — dan kalau terlewat, foto uji ikut dilatih. Tidak ada yang
gagal kalau itu terjadi; angka evaluasinya justru naik dan terlihat meyakinkan.
Merangkainya di sini membuat urutan yang benar jadi jalur termudah.

Langkah 3 sengaja BERHENTI dan menunggu manusia. Mutu kotak otomatis terbelah:
rak minimarket rapi hampir sempurna, etalase warung padat menghasilkan kotak
raksasa yang menelan satu baris rak, dan bucket triase masih menyimpan foto
pemandangan jalan. Penyaring isi otomatis sudah dicoba pakai CLIP dan gagal —
seluruh skor berdesak 0,246-0,393, foto jalan terverifikasi mendapat skor tepat
di median. Sepuluh menit mata manusia di lembar kontak lebih murah daripada tim
melabeli foto yang tidak layak.

Pakai (dari akar repo; satu baris per perintah):
    python -m scripts.pipa_dataset --foto "<folder>" --triase "<triase.json>" --keluar "<hasil>" --proyek "<slug>"

Tanpa `--jalankan` berhenti sebelum mengunggah, dan itu memang bawaannya.
"""
import argparse
import os
import subprocess
import sys

LANGKAH = 4


def jalankan(no, judul, argv):
    print(f"\n{'=' * 66}\n[{no}/{LANGKAH}] {judul}\n{'=' * 66}")
    r = subprocess.run([sys.executable, "-m", *argv])
    if r.returncode != 0:
        raise SystemExit(f"langkah {no} gagal (kode {r.returncode}) — pipa dihentikan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True, help="folder foto mentah dari Drive")
    ap.add_argument("--triase", required=True)
    ap.add_argument("--triase-baru")
    ap.add_argument("--keluar", required=True, help="folder hasil autolabel")
    ap.add_argument("--proyek", required=True, help="slug proyek Roboflow")
    ap.add_argument("--batch", default="gdino-ronde1")
    ap.add_argument("--frasa", default="a packaged product.")
    ap.add_argument("--ambang", type=float, default=0.25)
    ap.add_argument("--jalankan", action="store_true",
                    help="lanjutkan sampai mengunggah. Tanpa ini berhenti di langkah 3.")
    a = ap.parse_args()

    daftar = os.path.join(a.keluar, "daftar-uji.txt")
    os.makedirs(a.keluar, exist_ok=True)

    argv = ["scripts.testset", "--triase", a.triase, "--keluar", daftar]
    if a.triase_baru:
        argv += ["--triase-baru", a.triase_baru]
    jalankan(1, "Kunci daftar foto uji", argv)

    argv = ["scripts.autolabel_grounding", "--foto", a.foto, "--keluar", a.keluar,
            "--triase", a.triase, "--frasa", a.frasa, "--ambang", str(a.ambang)]
    if a.triase_baru:
        argv += ["--triase-baru", a.triase_baru]
    jalankan(2, "Kotak awal dari Grounding DINO", argv)

    jalankan(3, "Lembar kontak untuk triase manusia",
             ["scripts.lembar_kontak", "--sumber", a.keluar])

    argv = ["scripts.kirim_roboflow", "--sumber", a.keluar, "--proyek", a.proyek,
            "--daftar-uji", daftar, "--batch", a.batch]
    if a.jalankan:
        argv.append("--jalankan")
    jalankan(4, "Kirim ke Roboflow" + ("" if a.jalankan else " (laporan saja)"), argv)

    print(f"\n{'=' * 66}")
    if a.jalankan:
        print("Selesai. Buka Roboflow -> Annotate, betulkan kotaknya.")
        print("Tambahkan kotak yang terlewat, jangan cuma menghapus yang salah.")
    else:
        print("Berhenti sebelum mengunggah — ini bawaannya, bukan galat.")
        print(f"Periksa dulu {os.path.join(a.keluar, '_lembar-kontak')}/lembar-*.jpg,")
        print("buang foto yang tidak layak, baru ulangi dengan --jalankan.")


if __name__ == "__main__":
    main()
