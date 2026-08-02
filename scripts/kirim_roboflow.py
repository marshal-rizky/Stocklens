"""Kirim hasil autolabel_grounding ke Roboflow lewat SDK resmi.

KENAPA SDK, BUKAN MCP
---------------------
Per 2 Agustus 2026 TIDAK ADA MCP server Roboflow resmi — tidak di npm, tidak di
PyPI, dan tidak ada repo MCP di organisasi GitHub Roboflow. Yang beredar cuma
repo pihak ketiga tanpa bintang, dan server MCP semacam itu memegang API key
kita. Paket `roboflow` di PyPI adalah yang resmi; itu yang dipakai di sini.

is_prediction=True — INI YANG PALING PENTING
--------------------------------------------
Kotak dari Grounding DINO adalah tebakan mesin, bukan kebenaran. Dikirim dengan
`is_prediction=True`, Roboflow menaruhnya sebagai **prediksi menunggu review**,
bukan sebagai ground truth. Kalau dikirim sebagai ground truth, kotak yang
belum diperiksa siapa pun ikut terpakai melatih — persis bahaya yang ditulis di
PANDUAN-DATASET. Jangan ubah ini tanpa alasan yang bisa dijelaskan.

API KEY
-------
Dibaca dari environment `ROBOFLOW_API_KEY` saja, tidak pernah dari argumen
baris perintah — argumen tersimpan di riwayat shell dan terlihat di daftar
proses. Ambil key-nya di Roboflow → Settings → API Keys (pakai Private API Key).

    set ROBOFLOW_API_KEY=xxxxx          (cmd.exe, sesi ini saja)

Pakai (dari akar repo; satu baris):
    pip install roboflow
    python -m scripts.kirim_roboflow --sumber "<folder hasil autolabel>" --proyek "<nama-proyek>"

Tanpa `--jalankan` skrip hanya melaporkan apa yang AKAN dikirim dan berhenti.
Mengunggah ke akun orang adalah tindakan keluar; jangan sampai tidak sengaja.
"""
import argparse
import glob
import os
import shutil
import tempfile

BATCH = "gdino-ronde1"


def periksa_sumber(sumber):
    """Pastikan foldernya memang keluaran autolabel_grounding, bukan folder asal."""
    d_img = os.path.join(sumber, "images")
    d_lbl = os.path.join(sumber, "labels")
    for d in (d_img, d_lbl):
        if not os.path.isdir(d):
            raise SystemExit(f"tidak ada folder {d} — jalankan autolabel_grounding dulu")

    gambar = sorted(glob.glob(os.path.join(d_img, "*.jpg")))
    if not gambar:
        raise SystemExit(f"tidak ada .jpg di {d_img}")

    pasang, yatim, kotak = [], [], 0
    for g in gambar:
        txt = os.path.join(d_lbl, os.path.splitext(os.path.basename(g))[0] + ".txt")
        if not os.path.exists(txt):
            yatim.append(os.path.basename(g))
            continue
        with open(txt, encoding="utf-8") as fh:
            n = sum(1 for b in fh if b.strip())
        pasang.append((g, txt, n))
        kotak += n
    return pasang, yatim, kotak


def susun(pasang, tujuan):
    """Roboflow menuntut gambar dan .txt BERDAMPINGAN dalam satu folder split,
    plus data.yaml di akar. Keluaran autolabel memisah images/ dan labels/, jadi
    disusun ulang di folder sementara — folder asal tidak disentuh."""
    d = os.path.join(tujuan, "train")
    os.makedirs(d, exist_ok=True)
    for g, txt, _ in pasang:
        shutil.copy2(g, os.path.join(d, os.path.basename(g)))
        shutil.copy2(txt, os.path.join(d, os.path.basename(txt)))
    with open(os.path.join(tujuan, "data.yaml"), "w", encoding="utf-8") as fh:
        fh.write("train: train\nval: train\nnc: 1\nnames: ['produk']\n")
    return tujuan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", required=True, help="folder keluaran autolabel_grounding")
    ap.add_argument("--proyek", required=True, help="id proyek Roboflow (dibuat kalau belum ada)")
    ap.add_argument("--batch", default=BATCH)
    ap.add_argument("--ground-truth", action="store_true",
                    help="kirim sebagai ground truth, BUKAN prediksi. Baca docstring dulu.")
    ap.add_argument("--jalankan", action="store_true",
                    help="benar-benar unggah. Tanpa ini skrip cuma melapor.")
    a = ap.parse_args()

    pasang, yatim, kotak = periksa_sumber(a.sumber)
    prediksi = not a.ground_truth

    print(f"sumber : {a.sumber}")
    print(f"proyek : {a.proyek}")
    print(f"batch  : {a.batch}")
    print(f"kirim sebagai: {'PREDIKSI menunggu review' if prediksi else '*** GROUND TRUTH ***'}")
    print(f"\n{len(pasang)} foto, {kotak} kotak (rata-rata {kotak / max(1, len(pasang)):.1f}/foto)")
    tanpa = [p for p in pasang if p[2] == 0]
    if tanpa:
        print(f"{len(tanpa)} foto tanpa kotak — harus digambar manual di Roboflow")
    if yatim:
        print(f"\n{len(yatim)} foto TANPA berkas label, TIDAK akan dikirim:")
        for y in yatim[:5]:
            print(f"  - {y}")

    if not a.jalankan:
        print("\n-- laporan saja, belum ada yang dikirim --")
        print("Tambahkan --jalankan untuk benar-benar mengunggah.")
        return

    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit("ROBOFLOW_API_KEY belum diset. Lihat docstring skrip ini.")

    from roboflow import Roboflow

    tmp = tempfile.mkdtemp(prefix="roboflow-kirim-")
    try:
        susun(pasang, tmp)
        ws = Roboflow(api_key=key).workspace()
        print(f"\nmengunggah {len(pasang)} foto...")
        ws.upload_dataset(
            tmp, a.proyek,
            project_type="object-detection",
            batch_name=a.batch,
            is_prediction=prediksi,
            num_retries=2,
            num_workers=10,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nSelesai. Buka Roboflow → Annotate → batch "
          f"'{a.batch}' untuk membetulkan kotaknya.")
    print("Ingat: tambahkan kotak yang terlewat, jangan cuma menghapus yang salah.")


if __name__ == "__main__":
    main()
