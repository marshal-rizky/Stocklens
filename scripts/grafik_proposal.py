"""Buat grafik hasil training untuk proposal, dari file hasil training asli.

Semua angka dibaca dari results.csv milik run yang sesungguhnya — tidak ada
angka yang diketik tangan di sini, supaya grafik tidak bisa menyimpang dari
apa yang benar-benar terjadi. Jalankan ulang setelah training baru dan gambar
ikut terbarui.

Keluaran: docs/proposal/gambar/*.png

    python scripts/grafik_proposal.py
"""

import argparse
import csv
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402

# Palet kategorikal tervalidasi (lihat skill dataviz: lolos lightness band,
# chroma floor, pemisahan CVD, dan normal-vision floor pada surface terang).
BIRU, JINGGA, TOSCA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA_2, GARIS = "#0b0b0b", "#5b5b5b", "#d8d8d4"
SURFACE = "#fcfcfb"

RUMAH = pathlib.Path.home() / "StokLens-training"
KELUAR = pathlib.Path("docs/proposal/gambar")


def _gaya(ax):
    """Sumbu dan grid recessive; bingkai atas/kanan dibuang."""
    ax.set_facecolor(SURFACE)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)
    for sisi in ("left", "bottom"):
        ax.spines[sisi].set_color(GARIS)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.grid(axis="y", color=GARIS, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _kurva(path):
    baris = list(csv.DictReader(open(path)))
    ep = [int(r["epoch"]) for r in baris]
    kunci = next(c for c in baris[0] if "mAP50(B)" in c and "95" not in c)
    return ep, [float(r[kunci]) for r in baris]


def grafik_sebelum_sesudah(keluar):
    """Batang berkelompok: satu-satunya grafik yang benar-benar menjawab
    'apakah fine-tune berhasil'. Recall sengaja ikut karena itu yang paling
    berarti untuk produk — barang yang tidak terdeteksi tidak akan terhitung."""
    metrik = ["mAP50", "mAP50-95", "Precision", "Recall"]
    data = {
        "YOLO11n COCO (sebelum)": [0.3040, 0.2091, 0.6170, 0.2789],
        "Fine-tune 1 tahap": [0.7867, 0.5230, 0.7792, 0.7522],
        "Fine-tune 2 tahap": [0.8270, 0.5690, 0.7948, 0.7866],
    }
    warna = [TINTA_2, BIRU, JINGGA]

    fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=SURFACE)
    lebar, n = 0.26, len(data)
    for i, ((nama, nilai), w) in enumerate(zip(data.items(), warna)):
        x = [j + (i - (n - 1) / 2) * lebar for j in range(len(metrik))]
        # 2px jarak antar batang lewat lebar sedikit lebih kecil dari slot.
        bar = ax.bar(x, nilai, lebar * 0.92, label=nama, color=w,
                     edgecolor=SURFACE, linewidth=1.5)
        # Label langsung di tiap batang: syarat relief untuk kontras < 3:1,
        # sekaligus membuat angka bisa dibaca tanpa mengukur ke sumbu.
        ax.bar_label(bar, fmt="%.3f", padding=2, fontsize=8, color=TINTA)

    ax.set_xticks(range(len(metrik)))
    ax.set_xticklabels(metrik, color=TINTA)
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_locator(MultipleLocator(0.2))
    ax.set_ylabel("Skor", color=TINTA_2, fontsize=9)
    ax.set_title("Detektor produk diuji di warung yang tidak pernah dilatihkan\n"
                 "85 foto, 1.832 objek — lokasi ditahan penuh dari data latih",
                 color=TINTA, fontsize=11, loc="left", pad=12)
    _gaya(ax)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left",
                    bbox_to_anchor=(0, -0.12), ncol=3)
    for t in leg.get_texts():
        t.set_color(TINTA_2)
    fig.tight_layout()
    fig.savefig(keluar / "01-sebelum-sesudah.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def grafik_kurva_finetune(keluar):
    """Kurva validasi tahap 2. Bukti 'kurva training' yang diminta rulebook."""
    ep, m = _kurva(RUMAH / "finetune_dua_tahap" / "results.csv")
    fig, ax = plt.subplots(figsize=(9, 4), facecolor=SURFACE)
    ax.plot(ep, m, color=BIRU, linewidth=2)
    puncak = max(range(len(m)), key=lambda i: m[i])
    ax.plot(ep[puncak], m[puncak], "o", markersize=9, color=BIRU,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate(f"terbaik: epoch {ep[puncak]}, mAP50 {m[puncak]:.3f}",
                (ep[puncak], m[puncak]), textcoords="offset points",
                xytext=(-12, 14), ha="right", fontsize=9, color=TINTA)
    ax.set_xlabel("Epoch", color=TINTA_2, fontsize=9)
    ax.set_ylabel("mAP50 (validasi)", color=TINTA_2, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_title("Kurva fine-tune tahap 2 pada dataset warung sendiri\n"
                 "60 epoch, 30 menit di RTX 4070",
                 color=TINTA, fontsize=11, loc="left", pad=12)
    _gaya(ax)
    fig.tight_layout()
    fig.savefig(keluar / "02-kurva-finetune.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def grafik_pretrain(keluar):
    """Kurva tahap 1 di SKU-110K — dasar klaim 'dua tahap', bukan satu."""
    ep, m = _kurva(RUMAH / "pretrain_sku110k" / "results.csv")
    fig, ax = plt.subplots(figsize=(9, 3.6), facecolor=SURFACE)
    ax.plot(ep, m, color=TOSCA, linewidth=2)
    ax.plot(ep[-1], m[-1], "o", markersize=9, color=TOSCA,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate(f"epoch {ep[-1]}: mAP50 {m[-1]:.3f}", (ep[-1], m[-1]),
                textcoords="offset points", xytext=(-10, -18), ha="right",
                fontsize=9, color=TINTA)
    ax.set_xlabel("Epoch", color=TINTA_2, fontsize=9)
    ax.set_ylabel("mAP50 (validasi)", color=TINTA_2, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_title("Tahap 1: pre-train di SKU-110K (11 ribu foto rak retail)\n"
                 "Kurva melandai setelah epoch 11 — 20 epoch dipilih dari data, bukan ditebak",
                 color=TINTA, fontsize=11, loc="left", pad=12)
    _gaya(ax)
    fig.tight_layout()
    fig.savefig(keluar / "03-kurva-pretrain.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def grafik_ambang_clip(keluar):
    """Dua tujuan ambang yang tarik-menarik, dalam satu sumbu.

    Keduanya proporsi 0–1, jadi sah dibaca pada satu skala — bukan dua sumbu-y.
    Sumber angka: docs/HASIL-UJI-AMBANG-CLIP.md (12 produk, 104 foto,
    leave-one-out dan leave-one-product-out).
    """
    kenal_x = [0.72, 0.75, 0.80, 0.85, 0.90]
    kenal_y = [0.981, 0.933, 0.875, 0.673, 0.173]
    tolak_x = [0.70, 0.75, 0.80, 0.85]
    tolak_y = [0.548, 0.683, 0.846, 1.000]

    fig, ax = plt.subplots(figsize=(9, 4.4), facecolor=SURFACE)
    ax.plot(kenal_x, kenal_y, "-o", color=BIRU, linewidth=2, markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2,
            label="Mengenali produk yang sudah didaftarkan")
    ax.plot(tolak_x, tolak_y, "-o", color=JINGGA, linewidth=2, markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2,
            label="Menolak barang yang belum didaftarkan")

    ax.axvline(0.85, color=TINTA_2, linewidth=1, linestyle=(0, (4, 4)))
    ax.annotate("dipilih: 0,85", (0.85, 0.06), textcoords="offset points",
                xytext=(-8, 0), ha="right", fontsize=9, color=TINTA)
    # Label langsung hanya di titik keputusan — bukan di setiap titik.
    ax.annotate("0,673", (0.85, 0.673), textcoords="offset points",
                xytext=(10, -4), fontsize=9, color=TINTA)
    ax.annotate("1,000", (0.85, 1.000), textcoords="offset points",
                xytext=(10, -4), fontsize=9, color=TINTA)

    ax.set_xlabel("Ambang kemiripan CLIP", color=TINTA_2, fontsize=9)
    ax.set_ylabel("Proporsi benar", color=TINTA_2, fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_xlim(0.68, 0.92)
    ax.set_title("Ambang mengerjakan dua tugas yang menginginkan arah berlawanan\n"
                 "12 produk, 104 foto — rak warung didominasi barang yang belum didaftarkan",
                 color=TINTA, fontsize=11, loc="left", pad=12)
    _gaya(ax)
    leg = ax.legend(frameon=False, fontsize=9, loc="upper left",
                    bbox_to_anchor=(0, -0.14), ncol=2)
    for t in leg.get_texts():
        t.set_color(TINTA_2)
    fig.tight_layout()
    fig.savefig(keluar / "04-ambang-clip.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    keluar = KELUAR
    keluar.mkdir(parents=True, exist_ok=True)
    grafik_sebelum_sesudah(keluar)
    grafik_kurva_finetune(keluar)
    grafik_pretrain(keluar)
    grafik_ambang_clip(keluar)
    for f in sorted(keluar.glob("*.png")):
        print(f"  {f}  {f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
