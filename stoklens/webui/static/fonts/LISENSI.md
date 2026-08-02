# Lisensi font

Kedua berkas di folder ini di-host sendiri, **bukan** ditarik dari CDN. Alasannya
aplikasi harus jalan tanpa internet saat dijalankan lewat `docker compose` untuk
penilaian; `@font-face` yang menunjuk `fonts.gstatic.com` akan gagal diam-diam di
sana dan UI jatuh ke font sistem.

Keduanya berlisensi **SIL Open Font License 1.1 (OFL-1.1)**, yang mengizinkan
penggunaan komersial, penyertaan dalam repo, dan redistribusi — termasuk untuk
karya lomba. Tidak ada kewajiban royalti; kewajibannya adalah mencantumkan
atribusi seperti di bawah dan tidak menjual font-nya sendiri secara terpisah.

| Berkas | Keluarga | Perancang | Sumber | Lisensi |
|---|---|---|---|---|
| `fraunces-latin.woff2` | Fraunces | Undercase Type (Phaedra Charles, Flavia Zimbardi) | github.com/undercasetype/Fraunces | OFL-1.1 |
| `archivo-latin.woff2` | Archivo | Omnibus-Type (Héctor Gatti) | github.com/Omnibus-Type/Archivo | OFL-1.1 |

Teks lisensi lengkap: <https://openfontlicense.org/open-font-license-official-text/>

## Catatan teknis

Yang diunduh hanya **subset latin dasar** (blok `unicode-range` yang memuat
`U+0000-00FF`). Subset lain — cyrillic, greek, vietnamese — tidak dipakai UI
berbahasa Indonesia dan hanya menambah berat repo. Total keduanya ±100 KB.

Keduanya font variabel, jadi satu berkas melayani seluruh rentang berat yang
dipakai (`font-weight: 400 700` untuk Archivo, `600 700` untuk Fraunces). Jangan
menambah berkas per-berat — itu memperbesar repo tanpa manfaat.
