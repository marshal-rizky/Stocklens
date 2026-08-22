"""Render DRAFT-PROPOSAL.md jadi PDF, lengkap dengan diagram Mermaid.

Tidak ada pandoc di mesin ini, jadi jalurnya dirakit dari yang tersedia:
blok ```mermaid dirender jadi PNG lewat mermaid-cli, markdown diubah jadi HTML,
lalu Edge headless mencetaknya jadi PDF.

Mermaid dirender lebih dulu (bukan lewat <script> di halaman) supaya PDF-nya
tidak bergantung koneksi dan tidak bisa gagal diam-diam saat dicetak.

    python scripts/proposal_pdf.py
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import tempfile

EDGE = pathlib.Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Calibri, sans-serif; font-size: 10.5pt;
       line-height: 1.55; color: #16181d; max-width: 100%; }
h1 { font-size: 20pt; border-bottom: 2px solid #2a78d6; padding-bottom: 6px; }
h2 { font-size: 15pt; margin-top: 22px; color: #14213d;
     border-bottom: 1px solid #d8d8d4; padding-bottom: 4px; }
h3 { font-size: 12.5pt; margin-top: 16px; color: #14213d; }
h4 { font-size: 11pt; margin-top: 13px; color: #33383f; }
/* Judul tidak boleh jadi baris terakhir halaman. */
h1, h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; }
th, td { border: 1px solid #d8d8d4; padding: 5px 8px; text-align: left;
         vertical-align: top; }
th { background: #f2f5f9; }
/* max-height WAJIB. Tanpa ini diagram flowchart TB yang tinggi memakan
   hampir satu halaman penuh masing-masing, dan proposal 20 halaman membengkak
   jadi 40. Lebar tetap dibatasi halaman; tinggi yang menentukan jumlah halaman. */
img { max-width: 100%; max-height: 135mm; width: auto; height: auto;
      display: block; margin: 10px auto; object-fit: contain; }
/* Gambar dan tabel jangan terbelah dua halaman. */
img, table, pre { break-inside: avoid; page-break-inside: avoid; }
code { background: #f2f3f5; padding: 1px 4px; border-radius: 3px;
       font-family: Consolas, monospace; font-size: 9pt; }
pre { background: #f7f8fa; border: 1px solid #e2e4e8; border-radius: 5px;
      padding: 9px 11px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #2a78d6; margin: 12px 0; padding: 2px 14px;
             background: #f6f9fd; color: #33383f; }
hr { border: none; border-top: 1px solid #d8d8d4; margin: 20px 0; }
"""


# wrappingWidth WAJIB dinaikkan. Bawaannya sekitar 200px, jadi label panjang
# dipatah otomatis jadi beberapa baris — node ikut tinggi dan sempit, dan
# diagramnya membengkak ke bawah sampai harus diperkecil habis-habisan agar
# muat di halaman. Dengan label bertahan satu baris, node jadi lebar dan pendek,
# dan tumpukan flowchart TB jadi padat serta terbaca.
MMD_CONFIG = '{"flowchart": {"wrappingWidth": 820, "useMaxWidth": false}}'


def render_mermaid(teks: str, keluar: pathlib.Path) -> str:
    """Ganti tiap blok ```mermaid dengan <img> ke PNG hasil render."""
    keluar.mkdir(parents=True, exist_ok=True)
    blok = re.findall(r"```mermaid\n(.*?)```", teks, re.S)
    print(f"merender {len(blok)} diagram mermaid...")
    tmp = pathlib.Path(tempfile.mkdtemp())
    cfg = tmp / "mmd.json"
    cfg.write_text(MMD_CONFIG, encoding="utf-8")
    for i, isi in enumerate(blok, 1):
        mmd = tmp / f"d{i}.mmd"
        mmd.write_text(isi, encoding="utf-8")
        png = keluar / f"diagram-{i:02d}.png"
        r = subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli@11", "-i", str(mmd),
             "-o", str(png), "-b", "white", "-s", "2", "-c", str(cfg)],
            capture_output=True, text=True, shell=True)
        if not png.exists():
            raise SystemExit(f"diagram {i} gagal dirender:\n{r.stderr[-600:]}")
        print(f"  diagram {i}/{len(blok)}")
    shutil.rmtree(tmp, ignore_errors=True)

    n = iter(range(1, len(blok) + 1))
    return re.sub(r"```mermaid\n.*?```",
                  lambda _: f'<img src="{keluar.name}/diagram-{next(n):02d}.png" alt="diagram">',
                  teks, flags=re.S)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", default="docs/proposal/DRAFT-PROPOSAL.md")
    ap.add_argument("--keluar", default="docs/proposal/StokLens-Proposal.pdf")
    a = ap.parse_args()

    import markdown

    src = pathlib.Path(a.sumber)
    akar = src.parent
    teks = render_mermaid(src.read_text(encoding="utf-8"), akar / "diagram")

    isi = markdown.markdown(teks, extensions=["tables", "fenced_code", "sane_lists"])
    html = akar / "_proposal.html"
    html.write_text(f"<!doctype html><meta charset='utf-8'>"
                    f"<style>{CSS}</style>{isi}", encoding="utf-8")

    pdf = pathlib.Path(a.keluar).resolve()
    subprocess.run([str(EDGE), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri()],
                   capture_output=True, timeout=240)
    if not pdf.exists():
        raise SystemExit("Edge gagal menghasilkan PDF")
    print(f"selesai: {pdf}  ({pdf.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
