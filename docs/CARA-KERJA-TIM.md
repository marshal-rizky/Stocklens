# Cara Kerja Tim StokLens

> Aturan kerja untuk tim 3–5 orang, mode lomba, deadline 25 Agustus 2026.
> Dibuat 2026-07-28 dari audit terhadap rulebook AIC + kondisi repo.
>
> **Kenapa dokumen ini ada:** metodologi lama tidak buruk — justru bagus untuk
> satu orang. Tapi 9 dari 9 PR ditulis, di-review, dan di-merge oleh orang yang
> sama. Aturan "minimal 1 orang lain melihat sebelum merge" di CATATAN-TIM
> **tidak pernah benar-benar dijalankan.** Begitu jadi 3–5 orang, kebiasaan solo
> akan pecah di titik-titik yang sudah kelihatan di §5.

---

## 1. PRINSIP

1. **Deadline mengalahkan kesempurnaan.** 25 Agu 23.55 WIB. Fitur setengah jadi
   yang jujur didemokan lebih baik daripada fitur sempurna yang telat.
2. **Yang dinilai bukan cuma kode.** Kode = 25%. Video + proposal + kesiapan MVP
   = 45%. Jangan habiskan 90% waktu di 25% nilai.
3. **Jangan bangun di luar alur inti.** Rulebook menghukum *overbuilt*.
   Alur inti = enroll → scan → laporan selisih. Titik.
4. **Setiap klaim butuh bukti.** Juri tanya "berbasis data atau analisis?".
   Angka uji lapangan > opini.
5. **Commit adalah bagian dari penilaian.** Conventional Commits wajib per rulebook.

---

## 2. PERAN

Tim 3–5 orang. Satu orang boleh pegang >1 peran, tapi **setiap peran harus punya
nama**. Peran tanpa nama = pekerjaan tidak terjadi.

| Peran | Tanggung jawab | Output |
|---|---|---|
| **Ketua / Integrator** | Merge final, jaga scope, putuskan konflik, submit | Repo hijau, submisi tepat waktu |
| **Model** | Dataset, labeling QC, fine-tune YOLO, tabel baseline vs sesudah | `stoklens-yolo.pt` + kurva training |
| **Lapangan** | Izin toko, foto rak, uji lapangan, catat akurasi | ≥500 foto berlabel + tabel akurasi |
| **Naskah** | Proposal PDF, skrip video | Proposal ≤20 hal |
| **Produksi** | Rekam & edit 2 video, upload YouTube | 2 link YouTube sesuai format |

**Aturan penting:** peran Naskah & Produksi **tidak boleh** dipegang orang yang
sama dengan Model di minggu 4. Minggu 4 keduanya jalan bersamaan.

---

## 3. ALUR KERJA HARIAN

### Klaim pekerjaan sebelum mulai
Sebelum menyentuh kode, tulis di grup: **"ambil [item] — file yang kusentuh: X, Y"**.

Kenapa: dua orang di file yang sama = konflik. Repo ini punya file magnet
konflik: `api.py`, `report_view.js`, `app.js`, `db.py`.

### Batas file (siapa pegang apa)
| Area | File |
|---|---|
| Model & pipeline | `scan.py`, `photo.py`, `embedder.py`, `matcher.py`, `crossing.py`, `counter.py` |
| API | `api.py`, `db.py`, `report.py`, `accounting.py` |
| UI | `webui/**` |
| Docs | `docs/**`, `README.md` |

Dua orang di area sama → **ngobrol dulu**, jangan langsung branch.

### Siklus per pekerjaan
```
klaim di grup
  → git pull origin main
  → git checkout -b <tipe>/<nama-singkat>
  → kerjakan + tulis test
  → pytest hijau lokal
  → push, buka PR
  → review orang lain (§4)
  → CI hijau
  → merge
  → kabari grup "sudah merge, silakan pull"
```

### Format branch & commit
```
fitur/<nama>     feat: <deskripsi>
fix/<nama>       fix: <deskripsi>
docs/<nama>      docs: <deskripsi>
refactor/<nama>  refactor: <deskripsi>
```

**Wajib Conventional Commits — ini aturan rulebook, bukan selera.** Commit tanpa
pesan deskriptif "dapat dianggap tidak memenuhi standar pengembangan".

⚠️ **Jangan edit file lewat web GitHub.** Itu menghasilkan commit seperti
"Update CATATAN-TIM.md" yang melanggar konvensi. Sudah terjadi sekali (`d910bf9`).

---

## 4. REVIEW — INI YANG DULU TIDAK JALAN

### Aturan keras
1. **PR tidak boleh di-merge oleh penulisnya sendiri** kecuali sudah lewat 12 jam
   tanpa ada yang review DAN CI hijau DAN bukan file magnet konflik.
2. Reviewer wajib **menjalankan kodenya**, bukan cuma baca diff.
3. Review menghasilkan salah satu: `LGTM` / `LGTM dengan catatan` / `perlu perbaikan`.

### Yang dicek reviewer
- [ ] Ada test untuk logika baru?
- [ ] `pytest` hijau di mesin reviewer?
- [ ] Menyentuh file yang lagi dipegang orang lain?
- [ ] Menambah fitur **di luar alur inti**? (→ tolak, lihat §1.3)
- [ ] Commit message ikut konvensi?
- [ ] Ada rahasia/`.db`/`*.pt`/foto toko ikut ke-commit?

### Sub-agent-driven development — cara pakainya di tim
Pola lama (implement → spec review → quality review → fix loop) **terbukti
bekerja** — Unit 4 menemukan 4 Important + 2 Minor lewat 3 putaran, salah satunya
regresi yang lahir dari fix sebelumnya. Pertahankan, tapi:

- Sub-agent review **tidak menggantikan** review manusia. Ia menyaring dulu,
  manusia memutuskan.
- Hasil review yang penting **ditulis ke plan doc**, bukan hilang di chat.
  Ini yang bikin proposal nanti gampang — jejak iterasi sudah ada.
- Kalau sub-agent dan manusia beda pendapat → ketua yang putuskan, alasannya dicatat.

---

## 5. ATURAN ANTI-KONFLIK-SEMANTIK

**Sudah menggigit dua kali.** PR #16 menambah `fetch(` yang sah ke
`report_view.js`; guard test di branch lain melarang `fetch(` apa pun. Keduanya
hijau sendiri-sendiri, git merge bersih, CI merah **setelah** merge. Korban
berikutnya PR #19 — CI-nya gagal karena main saat itu belum punya perbaikannya.

### Aturan
1. **Kalau dua PR terbuka menyentuh file yang sama, yang merge belakangan WAJIB
   merge main ke branch-nya dan jalankan `pytest` sebelum minta merge.**
   Git bilang "no conflict" **tidak cukup**.
2. **Test guard harus menguji pola, bukan keberadaan kata.** Larang
   `res.status ===` (pola yang dibuang), jangan larang `fetch(` (alat yang sah).
3. **PR yang diam >3 hari wajib di-rebase/merge main sebelum dilanjutkan.**

---

## 6. IRAMA MINGGUAN

### Standup harian (5 menit, async di grup)
```
kemarin: ...
hari ini: ...
mentok di: ...
```

### Sync mingguan (30 menit, Minggu malam)
1. Cek posisi vs rencana 28 hari
2. Apa yang mundur? Perlu potong scope?
3. Bagi peran minggu depan
4. Update checklist

### Papan status
Satu file `STATUS.md` di repo, di-update tiap sync:
```markdown
## Minggu N (tanggal)
| Deliverable | PIC | Status | Blocker |
|---|---|---|---|
| docker compose | | belum | |
| dataset 500 foto | | 120/500 | izin toko ke-3 |
```

Kenapa file, bukan chat: chat hilang, file bisa dibaca orang yang baru gabung.

---

## 7. DEFINISI SELESAI

Sebuah pekerjaan **selesai** kalau:
- [ ] Test hijau (kalau ada logika)
- [ ] Di-review orang lain
- [ ] CI hijau
- [ ] Ter-merge ke main
- [ ] Docs ter-update kalau perilaku berubah
- [ ] Diumumkan di grup

**Deliverable lomba selesai** kalau:
- [ ] Sudah ter-upload di tempat yang benar (YouTube/situs COMPFEST)
- [ ] Format nama/durasi/visibility sesuai rulebook persis
- [ ] Dicek orang kedua

---

## 8. YANG TIDAK BOLEH MASUK GIT

Sudah di `.gitignore`, jangan di-force:
`*.db` • `*.pt` • video/foto uji • dataset • `data/crops/`

Share lewat Drive tim. **Foto toko mengandung nama usaha orang** — jangan sebar
ke luar tim.

---

## 9. ATURAN KHUSUS LOMBA

1. **Dilarang menunjukkan latar belakang institusi dalam bentuk apa pun** —
   cek proposal, kedua video, README, dan slide. Termasuk logo, nama kampus,
   email kampus, template kampus.
2. **Repo wajib public** dan commit terakhir sebelum 25 Agu 23.55 WIB.
3. **Setelah hackathon final selesai, dilarang keras mengubah repository.**
4. Karya wajib dikerjakan **hanya dalam periode 17 Juni – 25 Agustus 2026**.
   Repo ini dimulai ~9 Juli → aman.
5. **9 & 10 September 20.00 standby Discord** — bisa diminta live demo, wajib
   jawab ≤2 jam.
6. Finalis wajib hadir **luring** di Fasilkom UI: hackathon 10 jam (26 Sep) +
   live pitching & awarding (27 Sep). Pemenang tidak hadir = hilang hadiah.

---

## 10. KALAU MENTOK

| Situasi | Lakukan |
|---|---|
| CI merah dan tidak paham kenapa | Jangan merge. Tempel log ke grup. |
| Dua orang tabrakan di file sama | Yang belakangan merge main dulu + `pytest` |
| Fitur tidak selesai tepat waktu | Demokan apa adanya, jelaskan statusnya di video. Rulebook **membolehkan** fitur buggy asal jujur. |
| Ragu suatu fitur overbuilt | Tanya: "ini bagian dari enroll → scan → laporan?" Kalau bukan → jangan. |
| Ragu soal aturan | Tanya panitia: aic@compfest.id / Discord AIC. Jangan menebak. |
