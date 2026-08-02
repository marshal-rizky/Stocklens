"""Rekam perilaku detektor di test set yang disisihkan — pembanding "sebelum".

APA YANG DIUKUR, DAN APA YANG TIDAK
-----------------------------------
Skrip ini TIDAK menghitung mAP. mAP menuntut kotak kebenaran hasil labeling
manusia, dan per 2 Agustus 2026 belum ada satu pun label di proyek ini.
Angka akurasi apa pun yang dilaporkan tanpa label adalah karangan.

Yang direkam adalah PERILAKU detektor yang bisa diukur tanpa label:
jumlah kotak per foto, sebaran ukuran kotak, dan sebaran confidence. Itu cukup
untuk menjawab pertanyaan setelah fine-tune nanti:

  - apakah model jadi menemukan lebih banyak/lebih sedikit objek?
  - apakah model akhirnya bisa memprediksi kotak besar (sekarang mentok ~10%
    dari frame — lihat PANDUAN-FINETUNE Step 1.5)?
  - apakah model jadi lebih percaya diri pada foto warung?

Begitu label sudah ada, GANTI skrip ini dengan `model.val()` yang sesungguhnya.
Ini pengganti sementara, bukan tujuan akhir.

PEMILIHAN TEST SET
------------------
Logikanya ada di `scripts/testset.py`, dipakai bersama `kirim_roboflow.py` —
foto uji yang sama harus masuk split `test` di Roboflow, kalau tidak ia ikut
terlatih dan perbandingan sebelum/sesudah jadi tidak sah.

Keluarkan daftarnya dengan:
    python -m scripts.testset --triase triase.json --keluar daftar-uji.txt

Pakai:
    python -m scripts.baseline_detektor --triase <path triase.json> \
        [--triase-baru <path>] --foto <folder foto> --keluar baseline.json
"""
import argparse
import json
import os
from collections import defaultdict

import numpy as np

# Pemilihan test set tinggal di scripts/testset.py — dipakai bersama dengan
# kirim_roboflow.py. Kalau logikanya disalin ke sini lalu salah satu berubah,
# angka "sebelum" dan "sesudah" diukur di foto yang berbeda tanpa ada yang gagal.
from scripts.testset import domain, muat_triase, pilih_uji

CONF_PRODUKSI = 0.25   # ambang yang dipakai aplikasi
CONF_LABEL = 0.05      # ambang untuk auto-labeling (lihat PANDUAN-DATASET)


def ukur(model, foto, jalur, conf):
    per_foto, semua_luas, semua_conf = [], [], []
    for i in range(0, len(foto), 8):
        grup = foto[i:i + 8]
        for x, r in zip(grup, model.predict([jalur(g) for g in grup], conf=conf,
                                            imgsz=640, max_det=1000, verbose=False)):
            n = 0 if r.boxes is None else len(r.boxes)
            luas = []
            if n:
                wh = r.boxes.xywhn.cpu().numpy()
                luas = (wh[:, 2] * wh[:, 3] * 100).tolist()
                semua_conf.extend(r.boxes.conf.cpu().numpy().tolist())
                semua_luas.extend(luas)
            per_foto.append({"nama": x["nama"], "domain": domain(x), "kotak": n})
    return per_foto, np.array(semua_luas), np.array(semua_conf)


def ringkas(nama, per_foto, luas, conf):
    n = np.array([p["kotak"] for p in per_foto])
    out = {
        "conf": nama, "foto": len(per_foto), "total_kotak": int(n.sum()),
        "kotak_per_foto": {
            "median": float(np.median(n)), "p25": float(np.percentile(n, 25)),
            "p75": float(np.percentile(n, 75)), "maks": int(n.max()) if len(n) else 0,
            "foto_nol_kotak": int((n == 0).sum()),
        },
        "luas_kotak_persen_frame": {
            "median": round(float(np.median(luas)), 3) if len(luas) else None,
            "p99": round(float(np.percentile(luas, 99)), 3) if len(luas) else None,
            "maks": round(float(luas.max()), 3) if len(luas) else None,
            "di_atas_10_persen": int((luas > 10).sum()) if len(luas) else 0,
        },
        "confidence": {
            "median": round(float(np.median(conf)), 3) if len(conf) else None,
            "p25": round(float(np.percentile(conf, 25)), 3) if len(conf) else None,
        },
        "per_domain": {},
    }
    for d in sorted({p["domain"] for p in per_foto}):
        k = np.array([p["kotak"] for p in per_foto if p["domain"] == d])
        out["per_domain"][d] = {"foto": len(k), "median_kotak": float(np.median(k)),
                                "foto_nol_kotak": int((k == 0).sum())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triase", required=True)
    ap.add_argument("--triase-baru")
    ap.add_argument("--foto", required=True)
    ap.add_argument("--bobot", default=os.environ.get("STOKLENS_MODEL", "yolo11n.pt"))
    ap.add_argument("--keluar", default="baseline_detektor.json")
    a = ap.parse_args()

    semua = muat_triase(a.triase, a.triase_baru)
    jalur = lambda x: os.path.join(a.foto, f"{x['id']}__{x['nama']}")
    uji = [x for x in pilih_uji(semua) if os.path.exists(jalur(x))]
    print(f"test set: {len(uji)} foto  |  bobot: {a.bobot}\n")

    from ultralytics import YOLO
    model = YOLO(a.bobot)

    hasil = {"bobot": a.bobot, "jumlah_foto_uji": len(uji),
             "berkas_uji": sorted(x["nama"] for x in uji), "pengukuran": []}
    for conf in (CONF_PRODUKSI, CONF_LABEL):
        pf, luas, cf = ukur(model, uji, jalur, conf)
        r = ringkas(f"{conf}", pf, luas, cf)
        hasil["pengukuran"].append(r)
        print(f"--- conf={conf} ---")
        print(f"  total kotak      : {r['total_kotak']}")
        print(f"  kotak/foto       : median {r['kotak_per_foto']['median']:.0f}"
              f"  (p25 {r['kotak_per_foto']['p25']:.0f} – p75 {r['kotak_per_foto']['p75']:.0f})")
        print(f"  foto tanpa kotak : {r['kotak_per_foto']['foto_nol_kotak']} dari {r['foto']}")
        lk = r["luas_kotak_persen_frame"]
        print(f"  luas kotak       : median {lk['median']}%  maks {lk['maks']}%"
              f"  (>10% frame: {lk['di_atas_10_persen']})")
        print(f"  confidence       : median {r['confidence']['median']}")
        for d, v in r["per_domain"].items():
            print(f"    {d:12s} {v['foto']:3d} foto, median {v['median_kotak']:.0f} kotak,"
                  f" {v['foto_nol_kotak']} tanpa kotak")
        print()

    with open(a.keluar, "w", encoding="utf-8") as f:
        json.dump(hasil, f, indent=1)
    print(f"-> {a.keluar}")
    print("\nCATATAN: ini BUKAN mAP. Belum ada label, jadi akurasi belum terukur.")


if __name__ == "__main__":
    main()
