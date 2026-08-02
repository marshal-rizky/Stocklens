# Analisis Pembanding — Tunarasa (COMPFEST 17 AIC, 2025)

> **STATUS: CATATAN KERJA LOKAL, TIDAK DI-COMMIT.**
>
> Dianalisis 2026-07-29 dari dua sumber publik:
> - Repositori `github.com/ArielSulton/tunarasa` (AGPL-3.0)
> - Video promosi `youtube.com/watch?v=TPw_WnOy2dQ` — *"COMPFEST 17 AIC: TUNARASA
>   — Platform Komunikasi Inklusif untuk Aksesibilitas Layanan Publik"*,
>   7:23, diunggah 2025-08-24, 344 tayangan
>
> **Batas analisis ini:** proposal PDF dan video proof of work mereka tidak dapat
> diakses — padahal keduanya berbobot 15% dan 15%. Kesimpulan di bawah hanya
> menjangkau repo dan video promosi. Status "pemenang" diterima sebagai
> keterangan dari luar, tidak dapat diverifikasi dari kedua sumber ini.
>
> **Peringatan aturan:** ini COMPFEST **17** (2025). Beberapa batasan rulebook
> **18** tampaknya lebih ketat, khususnya soal ruang lingkup MVP dan durasi
> video. Jangan pakai video/repo mereka sebagai patokan kepatuhan.

---

## 1. Apa yang mereka bangun

Pengenalan bahasa isyarat SIBI + RAG Q&A supaya penyandang tunarungu dapat
mengakses layanan publik. Gesture tangan di browser → teks → dijawab LLM dengan
konteks dokumen instansi pemerintah → ringkasan percakapan lewat QR jadi PDF.

**Stack:** Next.js 15 + React 19 + Bun + Drizzle + Shadcn + MediaPipe +
TensorFlow.js di depan. FastAPI + LangChain + ChatGroq (LLaMA 3.3) + Pinecone +
Supabase + Redis + Prometheus + Grafana + DeepEval di belakang.

---

## 2. Data repositori

| | Tunarasa | StokLens (per 2026-07-29) |
|---|---|---|
| Rentang commit | 14 Jul – 24 Sep 2025 (~72 hari) | 9 – 29 Jul 2026 (~20 hari) |
| Jumlah commit | 118 | 121 |
| Kontributor | 2 orang (105 + 13 → satu orang 89%) | 2 akun, satu orang |
| Pull request | **4** | 32 |
| Branch | 2 (mayoritas commit langsung ke main) | branch per fitur |
| CI | **tidak ada** (folder `.github` tidak ada) | CI tiap PR + workflow Docker |
| Test | 9 file pytest, **butuh API key** (Groq/Pinecone/DeepEval) | 149 test, jalan **tanpa** torch |
| Dokumentasi | hanya README | 7 dokumen tim + plan doc per fitur |
| docker compose | ✓ dev + prod | ✓ diverifikasi di CI |

**Pola commit mereka meledak-ledak:** 21 commit pada 18 Agustus, 20 pada 17
Agustus, 8 pada 16 Agustus — **49 commit dalam 3 hari** persis sebelum deadline.

**Modul terbesar:** `langchain_service.py` 73 KB, `faq_recommendation_service.py`
56 KB, `document_manager.py` 45 KB.

### Kesimpulan bagian ini

**Kualitas proses repo bukan yang memenangkan lomba ini.** Proses mereka lebih
lemah daripada StokLens di hampir setiap ukuran yang bisa diperiksa — tanpa CI,
4 PR, commit langsung ke main, test yang tidak bisa jalan tanpa API key — dan
mereka tetap menang.

Yang menentukan ada di video, proposal, dan cerita dampak. Itu tepat 45% bobot
yang di StokLens masih 0.

---

## 3. Struktur video promosi mereka

| Waktu | Isi | Visual |
|---|---|---|
| 0:00–0:19 | Perkenalan tim, tiap orang menyebut nama & peran | 3 orang di depan dinding polos |
| 0:19–0:30 | Kait ke SDG 10 & 16 dan konsep smart city | Slide |
| 0:30–0:44 | **Masalah dengan angka**: 313.964 orang (0,4%) tunarungu di Indonesia, hanya 4,1% pakai alat bantu dengar | Donut chart + ikon orang |
| 0:44–1:27 | Solusi + 3 manfaat bernomor | Slide 01/02/03 |
| 1:27–1:54 | **Alur kerja pembuatan**: studi literatur → desain sistem → UI → backend+AI → integrasi Docker → testing → publish | Flowchart + screenshot Grafana |
| 1:54–2:46 | Tech stack + 3 aktor (user/admin/super admin) | Use-case diagram besar |
| 2:46–3:35 | Alur data & tabel | Diagram sangat padat |
| 3:35–4:13 | Arsitektur sistem | Diagram bersih dengan logo teknologi |
| 4:13–5:11 | **Evaluasi model dengan angka** | Donut + gauge chart |
| 5:11–7:16 | **Demo aplikasi** di domain publik `tunarasa.my.id` | Screen recording |
| 7:16–7:23 | Penutup | Kembali ke kamera |

**Teknik produksi:** presenter di-key (chroma) berdiri di depan slide sepanjang
video. Satu template, satu palet biru-putih, konsisten dari awal sampai akhir.
Semua anggota tampil dan berbicara.

---

## 4. Yang mereka lakukan benar — tiru ini

### 4.1 Masalah dikuantifikasi dalam 45 detik pertama
Bukan "banyak orang kesulitan", tapi angka konkret: *313.964 orang, 0,4%
populasi, hanya 4,1% punya alat bantu*. Di menit pertama.

### 4.2 Dikaitkan eksplisit ke SDG dan tema lomba
Melayani kriteria "Relevansi dengan Tema" (10%) tanpa juri harus menyimpulkan
sendiri.

### 4.3 Metodologi ditampilkan sebagai diagram DAN dinarasikan sebagai proses
Bukan "kami pakai FastAPI", tapi urutan pengerjaannya. Ini yang dicari rubrik
*"cerita proses perancangan dari ide sampai eksekusi dengan storytelling"*.

### 4.4 Rantai akurasi berlapis — momen teknis paling meyakinkan
Pada 4:24: *computer vision mendeteksi bahasa isyarat dengan akurasi **78%**,
LLM menyempurnakan teksnya, integrasi keduanya menaikkan akurasi ke **98%***.

Ditambah: LLM quality score 80%, pass rate 86,5%, answering ability 82%, dan
silhouette score 0,6 yang **dijustifikasi lewat hyperparameter tuning mencari K
terbaik**.

Ini bukan pamer angka. Ini keputusan arsitektur yang dibuktikan data — persis
yang dimaksud rubrik *"decision making berbasis data atau analisis"*.

### 4.5 Demo aplikasi nyata ~2 menit dari 7
Loop penuh sampai ringkasan percakapan lewat QR jadi PDF.

### 4.6 Presenter di-key di depan slide
Murah dilakukan (OBS + dinding polos + satu template slide) dan itulah yang
membuat video mereka terlihat rapi meski isinya padat.

---

## 5. Yang jangan ditiru

### 5.1 Durasi 7:23 untuk video promosi
Rulebook **18** mematok promosi **≤5 menit**. Aturan 17 mungkin berbeda — tidak
dapat dipastikan — tapi kalian terikat yang 5 menit. **Jangan pakai video mereka
sebagai patokan panjang.**

### 5.2 Dua diagram sama sekali tidak terbaca
Use-case di 2:22 dan alur data di 2:57: puluhan node biru kecil, tidak mungkin
dibaca dalam 15 detik. Fungsinya cuma memberi kesan "kami mengerjakan desain
serius". Berisiko dibaca juri sebagai pengisi durasi.

### 5.3 Kualitas produksi tidak konsisten
Segmen 6:04 adalah **ponsel merekam layar laptop** — miring, dinding terlihat —
sementara sisanya screen capture bersih. Terasa janggal.

### 5.4 Separuh durasi adalah eksposisi arsitektur dan tech stack
Itu bahan *proof of work*, bukan *promosi*. Video promosi seharusnya menjual
masalah dan solusi ke stakeholder.

### 5.5 Demo menampilkan super admin mengundang admin lewat email
Persis *"sistem otentikasi kompleks"* yang dilarang rulebook 18. Bukti visual
tambahan bahwa aturan scope di 18 kemungkinan reaksi terhadap video seperti ini.

### 5.6 Penutup meminta maaf atas kesalahan penyampaian
Konvensi lokal yang lazim, tapi di video promosi melemahkan kesan percaya diri.

---

## 6. Implikasi untuk StokLens — daftar tindakan

### 6.1 Turunkan kecemasan soal overbuilt, tetap jangan bangun apa pun baru

Tunarasa punya **ketiga hal** yang dilarang eksplisit rulebook 18 — dashboard
analitik tingkat lanjut, sistem otentikasi kompleks, halaman riwayat — dan tetap
menang. Dua tafsir yang tidak bisa dipisahkan dari bukti yang ada:

1. Batasan scope diperketat di 18 (bunyinya seperti reaksi terhadap hal ini)
2. Scope cuma 15%, mereka menang dari kriteria lain

Konsekuensi praktis sama untuk keduanya: **biaya membingkai ulang scope nol,
biaya membangun fitur baru tidak nol.** Rencana tidak berubah. Tapi penilaian
"overbuilt = risiko terbesar" di `AUDIT-RULEBOOK-2026-07-28.md` §3.3 **terlalu
keras** dan sebaiknya diturunkan kadarnya saat merevisi audit.

### 6.2 Bangun padanan momen "78% → 98%"

StokLens sudah punya bentuknya: **anti dobel-hitung berlapis**. Yang belum ada
angkanya.

**Tindakan:** saat uji lapangan, catat akurasi hitungan **di tiap lapis** —
deteksi mentah, lalu +tracking, lalu +ReID, lalu +line-crossing. Hasilnya rantai
angka yang sama persuasifnya dan lebih dalam secara teknis, karena menunjukkan
*tiga* keputusan berjenjang, bukan satu.

→ Tambahkan baris di `STATUS.md` minggu 3: **catat akurasi per lapis, bukan cuma
akurasi akhir.**

### 6.3 Angka model kalian sudah lebih kuat — pakai sebagai progresi

Mereka menampilkan satu angka akurasi akhir. StokLens punya **progresi
terukur**: mAP50 0,756 → 0,850 → 0,868 lintas epoch, tabel baseline vs sesudah
fine-tune, dan alasan berhenti di epoch 20 (kurva melandai, +0,018 dari epoch
11). Itu bukti *proses*, bukan cuma bukti *hasil*.

### 6.4 Adegan yang tim lain tidak bisa tiru

Seluruh pipeline mereka butuh internet — Groq untuk LLM, Pinecone untuk vector
DB, Supabase untuk auth. StokLens jalan lokal.

**Tindakan:** di video, **cabut koneksi internet lalu jalankan opname sampai
selesai.** Satu adegan, tanpa narasi, membuktikan klaim biaya per-scan nol dan
data tidak keluar toko. Tim yang bergantung API tidak bisa menirunya.

### 6.5 Inti emosional yang belum dipakai

Momen wow StokLens (menghitung barang di rak) kalah dramatis dibanding gesture
jadi teks. Tapi inti emosionalnya ada: **pemilik warung yang tidak pernah tahu
berapa rupiah dagangannya hilang tiap bulan.**

Pembuka video promosi bukan "sistem kami mendeteksi 155 objek", tapi angka nyata
dari warung pilot: *"Bu ⟨nama⟩ baru tahu kehilangannya Rp ⟨…⟩ sebulan."*

Ini juga keunggulan struktural: mereka memakai statistik nasional, kalian bisa
memakai **angka dari pengguna sungguhan** — lebih kuat karena lebih dekat.

### 6.6 README sebagai dokumen jualan

README mereka penuh badge, emoji, daftar fitur, dan diagram arsitektur ASCII.
README StokLens fungsional dan rendah hati. Karena repo adalah deliverable yang
dinilai, menambahkan diagram arsitektur (Mermaid, render otomatis di GitHub) dan
satu bagian singkat "apa yang membedakan ini" kemungkinan menolong.

Batasnya: jangan mengklaim berlebihan — itu paling gampang dibongkar saat live
demo standby Discord 9–10 September.

### 6.7 Catatan waktu

Commit terakhir mereka 24 September, dua hari sebelum hackathon final. Ledakan
commit pertengahan Agustus adalah snapshot yang dinilai di penyisihan.
Pengembangan **berlanjut** setelah penyisihan — aturan "stop commit sebelum
25 Agu 23.55" hanya mengunci snapshot penyisihan.

---

## 7. Rancangan struktur video promosi StokLens (5 menit)

Mengambil yang bekerja dari Tunarasa, membuang yang tidak.

| Waktu | Isi | Catatan |
|---|---|---|
| 0:00–0:20 | Perkenalan tim + satu kalimat "ini apa" | Semua anggota tampil, seperti mereka |
| 0:20–1:00 | **Masalah dengan angka nyata dari warung pilot** | Bukan statistik nasional — angka pengguna sungguhan lebih kuat |
| 1:00–1:30 | Solusi + 3 manfaat | Format bernomor terbukti mudah dicerna |
| 1:30–2:15 | **Metodologi sebagai diagram** | Pakai diagram arsitektur + anti-dobel-hitung dari draft proposal. **JANGAN** pakai ER diagram yang padat |
| 2:15–3:00 | **Evaluasi model dengan angka** | Progresi mAP50 + tabel baseline vs fine-tune + rantai akurasi per lapis (§6.2) |
| 3:00–4:40 | **Demo alur inti**: enroll → scan foto → laporan selisih rupiah → enroll-dari-scan | Sisipkan adegan cabut internet (§6.4) |
| 4:40–5:00 | Penutup | **Tanpa** permintaan maaf |

**Teknik produksi:** presenter di-key di depan slide, satu template, satu palet.
Kualitas rekaman konsisten — jangan campur screen capture dengan ponsel merekam
layar.

---

## 8. Yang masih perlu dicari

- **Proposal PDF mereka** — 15% bobot, tidak dapat diakses. Kalau ketemu, itu
  pembanding paling berharga yang tersisa.
- **Video proof of work mereka** — 7 menit, YouTube unlisted, jadi kemungkinan
  besar tidak akan ketemu. Yang menarik dari situ: bagaimana mereka memenuhi
  aturan "dilarang cut, wajib double screen + timestamp" sambil tetap enak
  ditonton.
- **Daftar finalis lain COMPFEST 17** — satu pembanding hanya memberi satu titik
  data. Kalau ada 2–3 repo finalis lain, pola yang benar-benar berulang jadi
  kelihatan.
