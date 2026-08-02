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

SPLIT `test` — JANGAN DILEWATI
-----------------------------
`baseline_detektor.py` sudah mengunci daftar foto uji dan merekam angka
"sebelum" di sana. Kalau foto-foto itu ikut masuk `train`, model dilatih pada
foto ujinya sendiri dan perbandingan sebelum/sesudah jadi tidak sah. Yang bikin
berbahaya: tidak ada yang gagal — hasilnya justru terlihat bagus.

Berikan `--daftar-uji`, dihasilkan oleh `scripts/testset.py`. Tanpa itu semua
foto masuk `train` dan skrip memperingatkan.

Pakai (dari akar repo; satu baris):
    pip install roboflow
    python -m scripts.testset --triase triase.json --keluar daftar-uji.txt
    python -m scripts.kirim_roboflow --sumber "<folder hasil autolabel>" --proyek "<nama-proyek>" --daftar-uji daftar-uji.txt

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


def muat_daftar_uji(jalur):
    """Nama-nama foto uji, satu per baris. Dihasilkan oleh scripts/testset.py."""
    if not jalur:
        return set()
    with open(jalur, encoding="utf-8") as fh:
        return {b.strip() for b in fh if b.strip()}


def split_untuk(nama_gambar, nama_uji):
    """Foto uji WAJIB masuk split `test`.

    Cocokkan nama berkas UTUH. Versi pertama juga menerima potongan setelah
    `__` sebagai kecocokan, dan itu salah: nama asli dari HP bisa kembar. Di 171
    foto rak ada 2 pasang bernama sama, dan pencocokan longgar itu menyeret satu
    foto latih ikut ke split test — 45 test, padahal daftarnya 44.
    """
    return "test" if os.path.basename(nama_gambar) in nama_uji else "train"


def susun(pasang, tujuan, nama_uji=frozenset()):
    """Roboflow menuntut gambar dan .txt BERDAMPINGAN dalam folder per split,
    plus data.yaml di akar. Keluaran autolabel memisah images/ dan labels/, jadi
    disusun ulang di folder sementara — folder asal tidak disentuh."""
    hitung = {"train": 0, "test": 0}
    for g, txt, _ in pasang:
        s = split_untuk(g, nama_uji)
        d = os.path.join(tujuan, s)
        os.makedirs(d, exist_ok=True)
        shutil.copy2(g, os.path.join(d, os.path.basename(g)))
        shutil.copy2(txt, os.path.join(d, os.path.basename(txt)))
        hitung[s] += 1
    with open(os.path.join(tujuan, "data.yaml"), "w", encoding="utf-8") as fh:
        fh.write("train: train\nval: train\ntest: test\nnc: 1\nnames: ['produk']\n")
    return hitung


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", required=True, help="folder keluaran autolabel_grounding")
    ap.add_argument("--proyek", required=True, help="id proyek Roboflow (dibuat kalau belum ada)")
    ap.add_argument("--batch", default=BATCH)
    ap.add_argument("--daftar-uji",
                    help="berkas daftar foto uji dari scripts/testset.py. "
                         "Foto-foto itu ditaruh di split `test`, bukan `train`.")
    ap.add_argument("--ground-truth", action="store_true",
                    help="kirim sebagai ground truth, BUKAN prediksi. Baca docstring dulu.")
    ap.add_argument("--jalankan", action="store_true",
                    help="benar-benar unggah. Tanpa ini skrip cuma melapor.")
    a = ap.parse_args()

    pasang, yatim, kotak = periksa_sumber(a.sumber)
    nama_uji = muat_daftar_uji(a.daftar_uji)
    prediksi = not a.ground_truth
    n_uji = sum(1 for g, _, _ in pasang if split_untuk(g, nama_uji) == "test")

    print(f"sumber : {a.sumber}")
    print(f"proyek : {a.proyek}")
    print(f"batch  : {a.batch}")
    print(f"kirim sebagai: {'PREDIKSI menunggu review' if prediksi else '*** GROUND TRUTH ***'}")
    print(f"\n{len(pasang)} foto, {kotak} kotak (rata-rata {kotak / max(1, len(pasang)):.1f}/foto)")
    print(f"split  : {len(pasang) - n_uji} train, {n_uji} test")
    if not nama_uji:
        print("\n!! --daftar-uji tidak diberikan: SEMUA foto masuk train.")
        print("   Kalau foto uji ikut terlatih, perbandingan sebelum/sesudah")
        print("   tidak sah dan tidak akan ada yang gagal — angkanya cuma bohong.")
        print("   Keluarkan daftarnya: python -m scripts.testset --triase triase.json")
    elif n_uji != len(nama_uji):
        # Jumlah harus persis sama. Lebih = nama kembar tertarik ikut; kurang =
        # foto uji tidak ketemu dan diam-diam masuk train. Dua-duanya merusak
        # perbandingan tanpa menimbulkan galat, jadi harus berisik di sini.
        print(f"\n!! TIDAK COCOK: daftar uji {len(nama_uji)} nama, tapi {n_uji} foto"
              " tertandai test.")
        print("   Hentikan dan periksa — jangan diunggah. Penyebab lazim: nama")
        print("   berkas di --sumber tidak sama dengan yang ditulis testset.py.")
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
        hitung = susun(pasang, tmp, nama_uji)
        ws = Roboflow(api_key=key).workspace()
        print(f"\nmengunggah {hitung['train']} train + {hitung['test']} test...")
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
