# DRAFT PROPOSAL — StokLens

> **STATUS: DRAFT LOKAL, BELUM DI-COMMIT.**
>
> Diagram memakai sintaks Mermaid — ter-render otomatis di GitHub, VS Code
> (ekstensi Markdown Preview Mermaid), Obsidian, dan https://mermaid.live
> (tempel kode di dalam blok ```mermaid, unduh sebagai PNG/SVG untuk ditempel
> ke Word/Docs).
>
> **Sebelum dikirim, wajib dibereskan:**
> - Semua penanda `⟨…⟩` diisi (nama tim, nama anggota, angka uji lapangan).
> - Bagian bertanda 🔴 masih menunggu data lapangan — jangan dikarang.
> - **Hapus semua jejak institusi** (nama kampus, email kampus, logo, template).
> - Batas **20 halaman** di luar cover, daftar pustaka, dan lampiran.
> - Cek plagiarisme sebelum submit.

---

## 1. Nama Tim dan Judul Proyek

**Nama tim:** ⟨nama tim⟩

**Judul:** StokLens — Stock Opname Otomatis Berbasis Visi Komputer untuk Warung
dan Toko Kelontong

**Anggota:** ⟨nama 1⟩ · ⟨nama 2⟩ · ⟨nama 3⟩ ⟨…⟩

**Tema:** Smart Logistics

---

## 2. Latar Belakang

### 2.1 Masalah

Warung Madura dan toko kelontong kecil menyimpan ratusan SKU dalam ruang sempit,
tetapi hampir tidak pernah melakukan stock opname. Alasannya bukan kemalasan,
melainkan biaya: menghitung manual satu warung memakan waktu berjam-jam dan
harus dilakukan saat toko tutup. Akibatnya pemilik tidak pernah tahu tiga angka
yang menentukan kelangsungan usahanya:

1. **Berapa nilai rupiah barang yang ada di rak sekarang.**
2. **Berapa banyak barang yang hilang** tanpa tercatat sebagai penjualan
   (*shrinkage*) — rusak, kedaluwarsa, salah hitung, atau hilang.
3. **Barang mana yang mendekati kedaluwarsa** sebelum berubah jadi kerugian.

Solusi yang ada di pasar tidak menjawab kondisi ini. Aplikasi stock opname
berbasis barcode mensyaratkan setiap barang punya barcode yang terbaca dan
di-scan satu per satu — untuk warung dengan sachet renceng dan barang curah,
syarat itu tidak terpenuhi. Sistem RFID mensyaratkan pemasangan tag per item,
biaya yang tidak masuk akal untuk barang seharga Rp 500.

### 2.2 Posisi terhadap solusi sejenis

Sudah ada pemain yang menggarap arah serupa — antara lain WarungVision dan fitur
"Smart AI Stock Opname" pada beberapa perangkat lunak kasir. **Kami tidak
mengklaim sebagai yang pertama.** Yang membedakan StokLens ada lima, dan
semuanya dapat ditunjukkan, bukan sekadar dinyatakan:

| Pembeda | Penjelasan |
|---|---|
| **Enrollment few-shot, nol retraining di lapangan** | Barang baru didaftarkan dengan 3–5 foto. Tidak ada proses training yang harus dijalankan pemilik warung. |
| **Menghitung *facing* di rak** | Sistem menghitung barang yang benar-benar terlihat di rak, bukan membaca angka dari dokumen laporan lewat OCR. |
| **Anti dobel-hitung berlapis** | Tiga mekanisme independen; dirinci di §4.3. |
| **Memperbaiki diri sendiri dari pemakaian** | Barang yang gagal dikenali dapat diberi nama oleh pengguna, dan potongan gambarnya langsung memperkaya galeri pengenalan. |
| **Berjalan lokal, tanpa API pihak ketiga** | Seluruh inferensi berjalan di perangkat sendiri. Biaya per-scan nol, dan foto dagangan tidak pernah keluar dari toko. Pembeda paling tajam terhadap solusi yang bergantung pada layanan AI berbayar. |

Poin terakhir bukan sekadar keunggulan teknis. Bagi pemilik warung, model bisnis
berbasis biaya per-panggilan-API berarti biaya yang tumbuh seiring pemakaian —
justru menghukum pengguna yang paling rajin melakukan opname.

---

## 3. Tujuan dan Manfaat

### 3.1 Tujuan

1. Pemilik warung dapat menyelesaikan opname satu rak **dalam hitungan menit**
   menggunakan kamera ponsel yang sudah dimilikinya, tanpa perangkat tambahan.
2. Hasilnya berupa **laporan selisih dalam rupiah**, bukan sekadar daftar angka
   deteksi — sehingga langsung dapat ditindaklanjuti.
3. Sistem **dapat dijalankan sepenuhnya offline** di satu laptop atau ponsel,
   tanpa langganan dan tanpa mengirim data ke pihak ketiga.

### 3.2 Manfaat

**Bagi pemilik usaha:** mengetahui nilai stok dan angka kehilangan yang selama
ini tidak terukur; peringatan dini barang mendekati kedaluwarsa; dasar
pengambilan keputusan pembelian ulang.

**Bagi ekosistem UMKM:** menurunkan ambang masuk pencatatan stok yang selama ini
hanya terjangkau ritel modern.

**Aspek etika dan privasi:** SOP pengambilan foto secara eksplisit melarang
memotret orang — hanya rak barang. Seluruh data tersimpan lokal.

---

## 4. Metodologi

### 4.1 Arsitektur sistem

Aturan arsitektur yang dipegang sejak awal: **logika murni dipisah dari
pembungkus model berat.** Seluruh pustaka berat (`torch`, `ultralytics`,
`easyocr`) hanya diimpor di dalam fungsi atau di satu modul pembungkus, tidak
pernah di tingkat modul yang memuat logika.

Konsekuensinya dapat diuji, bukan diklaim: **seluruh test cepat berjalan tanpa
`torch` terpasang**, dan pipeline CI membuktikannya pada setiap pull request
karena lingkungan CI memang sengaja tidak memasang tumpukan torch.

```mermaid
flowchart TB
    subgraph UI["Antarmuka — mobile web, tanpa toolchain build"]
        A1["Beranda KPI"]
        A2["Katalog & enrollment"]
        A3["Opname: foto / video / manual"]
        A4["Laporan selisih"]
    end

    subgraph API["Lapisan API — FastAPI"]
        B1["/products — enrollment"]
        B2["/api/scans-foto"]
        B3["/scans — video"]
        B4["/report/{id}"]
        B5["/api/unknown/... — beri nama"]
    end

    subgraph CORE["Logika murni — TANPA torch, teruji di CI"]
        C1["matcher.py<br/>cosine + galeri"]
        C2["crossing.py<br/>line-crossing"]
        C3["counter.py<br/>agregasi track"]
        C4["expiry.py<br/>parser tanggal"]
        C5["report.py<br/>selisih & rupiah"]
        C6["accounting.py<br/>nilai stok, margin"]
    end

    subgraph HEAVY["Pembungkus model — impor malas"]
        D1["YOLO11n<br/>deteksi produk"]
        D2["CLIP ViT-B/32<br/>embedding"]
        D3["EasyOCR<br/>teks kemasan"]
    end

    subgraph DATA["Penyimpanan"]
        E1[("SQLite<br/>satu berkas")]
        E2["data/crops/<br/>potongan gambar"]
    end

    UI --> API
    API --> CORE
    API --> HEAVY
    CORE --> DATA
    HEAVY --> CORE
```

**Keputusan: SQLite satu berkas, bukan basis data terpisah.** Target pengguna
adalah warung dengan ratusan SKU, bukan ribuan cabang. SQLite menghilangkan
kebutuhan menjalankan layanan basis data, membuat seluruh aplikasi dapat
dijalankan dengan satu perintah `docker compose up`, dan membuat cadangan data
sesederhana menyalin satu berkas.

### 4.2 Alur inti: enroll → scan → laporan selisih

```mermaid
flowchart LR
    S1["1 · ENROLL<br/>3–5 foto per barang<br/>+ harga modal, stok awal"]
    S2["2 · SCAN<br/>foto rak atau video sweep"]
    S3["3 · LAPORAN<br/>selisih fisik vs tercatat<br/>dinilai rupiah"]
    S4["4 · TERAPKAN<br/>tulis ke buku stok"]

    S1 --> S2 --> S3 --> S4
    S3 -. "item tak dikenali<br/>diberi nama" .-> S1
```

Panah putus-putus adalah kunci akurasi jangka panjang dan dirinci di §4.5.

### 4.3 Alur pengembangan tiap fitur

#### 4.3.1 Enrollment — pengenalan tanpa retraining

```mermaid
flowchart TB
    F1["Pengguna memotret barang<br/>3–5 sudut"] --> F2["CLIP ViT-B/32<br/>ubah tiap foto jadi vektor"]
    F2 --> F3["Rata-ratakan vektor,<br/>normalisasi ulang"]
    F3 --> F4[("products.embedding<br/>+ nama, harga, stok awal")]
```

**Keputusan: CLIP zero-shot, bukan melatih pengklasifikasi.** Melatih
pengklasifikasi berarti setiap warung harus melatih ulang model setiap kali
menambah barang — mustahil dijalankan pemilik warung. Dengan pembandingan
embedding, menambah barang cukup menambah satu baris di basis data.

#### 4.3.2 Mode FOTO — jalur utama untuk warung

```mermaid
flowchart TB
    P1["Foto rak<br/>1 foto = 1 sub-segmen"] --> P2["YOLO11n<br/>deteksi kotak produk"]
    P2 --> P3{"untuk tiap kotak"}
    P3 --> P4["Potong gambar → CLIP → vektor"]
    P4 --> P5["Cocokkan ke galeri<br/>ambil similarity tertinggi"]
    P5 --> P6{"skor ≥ ambang 0,85?"}
    P6 -- ya --> P7["Tandai sebagai produk X"]
    P6 -- tidak --> P8["Tandai 'belum dikenali'<br/>simpan potongan + vektor"]
    P7 --> P9["Agregasi per produk<br/>+ rincian per foto"]
    P8 --> P9
    P9 --> P10["OCR tanggal kedaluwarsa<br/>pada potongan yang dikenali"]
    P10 --> P11[("scan_items")]
```

**Keputusan: mode foto jadi mode utama, bukan video.** Dalam satu foto, satu
deteksi = satu barang, sehingga seluruh kelas masalah "satu barang terhitung dua
kali karena ID tracking pecah" tidak pernah muncul. Mode foto juga jauh lebih
murah — enam foto sekitar 18 MB dibanding video sekitar 75 MB — dan OCR lebih
akurat karena foto diam lebih tajam daripada frame video yang blur karena
gerakan. Untuk warung yang sempit, mundur beberapa langkah untuk merekam sweep
sering kali tidak mungkin.

Risikonya berpindah ke antar-foto: zona tumpang tindih bisa terhitung dua kali.
Mitigasinya SOP satu foto satu sub-segmen berbatas fisik, ditambah **rincian
hitungan per foto** yang ditampilkan di antarmuka sehingga pengguna dapat
melihat dan mengoreksi sendiri.

#### 4.3.3 Mode VIDEO — untuk rak panjang

```mermaid
flowchart TB
    V1["Video sweep satu arah"] --> V2["YOLO11n + BoT-SORT + ReID<br/>track_buffer 60"]
    V2 --> V3["Per track: rekam riwayat posisi-x,<br/>ambil embedding tiap 5 frame,<br/>simpan potongan terbesar"]
    V3 --> V4["Line-crossing:<br/>track dihitung hanya bila<br/>menyeberang garis tengah<br/>searah sweep"]
    V4 --> V5["Cocokkan tiap sampel embedding,<br/>ambil label suara terbanyak"]
    V5 --> V6["Buang track berumur < 3 frame"]
    V6 --> V7["Agregasi per produk"]
    V7 --> V8["OCR pada potongan terbesar"]
    V8 --> V9[("scan_items")]
```

**Arah sweep tidak perlu dideklarasikan pengguna** — ditentukan otomatis dari
mayoritas arah penyeberangan seluruh track.

#### 4.3.4 Anti dobel-hitung — tiga lapis independen

Ini masalah paling menentukan pada mode video, dan diselesaikan berlapis karena
tidak ada satu mekanisme yang cukup:

```mermaid
flowchart TB
    L0["Deteksi mentah tiap frame<br/>(satu barang muncul di puluhan frame)"]
    L1["LAPIS 1 — Tracking<br/>hitung per track ID, bukan per deteksi"]
    L2["LAPIS 2 — ReID + track_buffer<br/>menyambung ID yang putus<br/>karena blur / terhalang"]
    L3["LAPIS 3 — Line-crossing + histeresis<br/>hanya hitung saat menyeberang garis"]
    L4["Filter umur track<br/>buang track < 3 frame"]
    L5["Hitungan akhir"]

    L0 --> L1 --> L2 --> L3 --> L4 --> L5
```

Alasan tiap lapis, dan apa yang gagal ditangani lapis sebelumnya:

| Lapis | Menangani | Yang masih lolos |
|---|---|---|
| Tracking | Satu barang di banyak frame | ID pecah → barang sama dapat dua ID |
| ReID + buffer | ID pecah karena blur/terhalang sesaat | ID pecah yang terlalu jauh jaraknya |
| Line-crossing | ID pecah di sisi layar yang sama — hanya satu yang sempat menyeberang | Track sangat pendek dari noise |
| Filter umur | Noise berumur pendek | — |

Histeresis pada line-crossing menyerap goyangan kamera kecil di sekitar garis.
Penyeberangan balik menghasilkan event bernilai −1 yang saling menghapus dengan
+1 sebelumnya, sehingga hitungan **mengoreksi dirinya sendiri** ketika kamera
sempat mundur.

#### 4.3.5 OCR tanggal kedaluwarsa

Parser menangani format yang benar-benar dipakai kemasan Indonesia: `EXP`, `ED`,
`BB`, `BAIK SEBELUM`, `BEST BEFORE`, dengan pola tanggal-bulan-tahun,
nama-bulan-tahun (`AGU 26`, `DES 2026`), maupun bulan-tahun. Nama bulan Indonesia
dan Inggris dipetakan bersamaan karena keduanya lazim ditemukan pada kemasan yang
sama.

### 4.4 Alur perolehan dataset

```mermaid
flowchart TB
    D1["Izin 2–3 warung Madura<br/>imbalan: hasil opname gratis"]
    D2["Foto rak resolusi penuh<br/>variasi jarak, sudut, cahaya, kepadatan"]
    D3["Unggah ke penyimpanan bersama<br/>subfolder per pemotret"]
    D4["Auto-label dengan detektor berbasis teks<br/>ambang rendah, sengaja berlebih"]
    D5["Koreksi manusia di Roboflow<br/>satu kelas: produk"]
    D6["QC ketua: sampling 10%"]
    D7["Normalisasi label:<br/>poligon → kotak"]
    D8["Split per LOKASI:<br/>satu warung ditahan penuh"]

    D1 --> D2 --> D3 --> D4 --> D5 --> D6 --> D7 --> D8
    D6 -. "kotak longgar / barang kelewat" .-> D5
```

**Keputusan: split per lokasi, bukan split acak.** Ini dua langkah terakhir di
atas, dan keduanya lahir dari kegagalan yang diuraikan di §5.2. Split acak
bawaan akan menaruh foto yang nyaris kembar — 3–5 jepretan rak yang sama dalam
hitungan detik — di data latih *dan* data uji sekaligus. Angka yang keluar akan
terlihat jauh lebih baik dan tidak berarti apa-apa.

**Keputusan: satu kelas `produk` saja, bukan satu kelas per merek.** Detektor
hanya perlu menjawab "di mana ada barang"; pengenalan merek dikerjakan CLIP.
Pemisahan ini membuat pekerjaan pelabelan jauh lebih cepat **dan** membuat
penambahan barang baru tidak memerlukan pelabelan ulang apa pun.

**Keputusan: menolak scraping marketplace.** Selain melanggar ketentuan layanan
dan hak cipta, jenis datanya salah — foto katalog berlatar putih, bukan adegan
rak. Model yang dilatih dengan data seperti itu justru belajar bias yang tidak
pernah ada di gudang.

**Keputusan: foto diambil di warung Madura, bukan grosir.** Model dasar sudah
dilatih pada rak supermarket; jika data sendiri juga diambil di lingkungan rapi
seperti grosir, satu jurang domain ditutup sementara jurang kedua dibuka. Ciri
warung yang tidak ada pada dataset supermarket: **sachet renceng yang
digantung**, cahaya bohlam hangat, rak improvisasi, dan ruang sempit.

**Keputusan pelabelan renceng: satu sachet = satu kotak.** Alasannya bukan teknis
melainkan bisnis — warung menjual dan menghitung stoknya per sachet. Jika model
menghitung per renceng, angka selisih pada laporan tidak akan cocok dengan cara
pemilik warung menghitung, dan seluruh fitur kehilangan maknanya baginya.

### 4.5 Perbaikan akurasi lewat pemakaian

Analisis kegagalan pencocokan menunjukkan penyebab utamanya **bukan** kemiripan
antar produk, melainkan **ketidakcocokan kondisi**: foto enrollment diambil
dekat, terang, dan tegak lurus, sementara potongan hasil scan berukuran kecil,
agak blur, dan menyerong. Urutan faktor perusak, dari yang paling parah:

1. Perbedaan skala dan ketajaman
2. Perbedaan cahaya dan suhu warna
3. Perbedaan sudut
4. Latar belakang rak
5. Foto stok dari internet — paling buruk, karena desain kemasannya sering
   sudah versi lama

Solusinya menghilangkan ketidakcocokan itu di akarnya:

```mermaid
flowchart TB
    U1["Scan menghasilkan item<br/>'belum dikenali'"] --> U2["Potongan gambarnya<br/>ditampilkan di laporan"]
    U2 --> U3["Pengguna menekan<br/>'Ini barang apa?'"]
    U3 --> U4{"Pilih"}
    U4 -- "produk yang sudah ada" --> U5["Vektor potongan ditambahkan<br/>ke galeri produk itu"]
    U4 -- "barang baru" --> U6["Buat produk baru<br/>dengan vektor potongan itu"]
    U5 --> U7[("product_embeddings")]
    U6 --> U7
    U7 --> U8["Scan berikutnya mengenali<br/>barang itu — galerinya kini<br/>berisi referensi dalam<br/>kondisi scan yang sama"]
```

**Keputusan: galeri banyak-vektor, BUKAN merata-ratakan.** Ini keputusan yang
sempat diambil salah lalu dikoreksi. Rencana awal adalah merata-ratakan vektor
enrollment dengan vektor potongan scan. Analisis menunjukkan hasilnya justru
buruk: merata-ratakan foto tampak-depan yang rapi dengan potongan menyerong yang
blur menghasilkan vektor yang **tidak mirip keduanya**. Yang akhirnya dibangun
adalah galeri berisi entri terpisah, dan pencocokan mengambil **similarity
tertinggi** di antara seluruh entri milik produk tersebut.

**Keputusan: vektor dihitung saat scan, bukan saat pengguna memberi nama.**
Konsekuensinya endpoint pemberian nama tidak perlu memuat CLIP sama sekali —
responsnya cepat dan dapat diuji tanpa torch. Biayanya sekitar 2 KB per potongan.

### 4.6 Alur integrasi model ke lingkungan kode

Model diperlakukan sebagai **dependensi yang dapat ditukar**, bukan bagian dari
kode. Bobot model tidak pernah masuk ke repositori — dibagikan lewat penyimpanan
bersama tim, dan repositori memblokirnya lewat `.gitignore`.

```mermaid
flowchart LR
    M1["yolo11n.pt<br/>COCO generik"] -->|"Tahap 1<br/>pre-train"| M2["SKU-110K<br/>11 rb foto rak retail"]
    M2 --> M3["Model paham<br/>'rak padat produk'"]
    M3 -->|"Tahap 2<br/>fine-tune"| M4["Dataset warung sendiri"]
    M4 --> M5["stoklens-yolo.pt"]
    M5 --> M6["Ditukar lewat parameter<br/>model_path — tanpa<br/>mengubah kode pipeline"]
```

**Keputusan: pre-train dua tahap, bukan langsung fine-tune dari COCO.** Dataset
sendiri terlalu kecil untuk mengajarkan bentuk umum "rak penuh produk yang
rapat". SKU-110K mengajarkan itu; dataset sendiri mengajarkan kondisi lokal.

**Hasil Tahap 1 yang sudah dicapai** (RTX 4070, 20 epoch, 37 menit):

![Kurva pre-train SKU-110K](gambar/03-kurva-pretrain.png)

| Epoch | mAP50 | mAP50-95 |
|---|---|---|
| 1 | 0,756 | 0,408 |
| 11 | 0,850 | 0,505 |
| **20 (final)** | **0,868** | **0,525** |

Validasi akhir pada 588 gambar berisi 90.968 objek: presisi 0,894, recall 0,816,
waktu inferensi 1,7 ms per gambar. Kurva sudah melandai — dari epoch 11 ke 20
hanya naik 0,018 — sehingga 20 epoch dinilai sebagai titik henti yang tepat,
bukan angka yang dipilih sembarangan.

**Hasil Tahap 2 (22 Agustus 2026).** Fine-tune dijalankan pada dataset warung
sendiri, 60 epoch, 30 menit di RTX 4070.

![Kurva fine-tune tahap 2](gambar/02-kurva-finetune.png)

#### Cara pengujian, dan kenapa caranya begitu

Angka di bawah ini diukur pada **85 foto dari satu warung yang seluruhnya
ditahan dari data latih** — model tidak pernah melihat satu pun foto dari lokasi
itu. Pilihan ini disengaja dan penting.

Split acak bawaan Roboflow akan memberi angka yang jauh lebih tinggi, tetapi
tidak sah: SOP pemotretan kami mengambil 3–5 foto per rak dalam hitungan detik,
sehingga foto yang nyaris kembar akan tersebar ke data latih *dan* data uji.
Model akan dinilai pada rak yang sudah pernah dilihatnya. Angka yang keluar
mengukur ingatan, bukan kemampuan menghadapi warung baru — dan warung baru
persis yang dihadapi produk ini setiap kali dipasang di toko berikutnya.

![Perbandingan sebelum dan sesudah fine-tune](gambar/01-sebelum-sesudah.png)

| Pengukuran | YOLO11n COCO (sebelum) | Fine-tune 1 tahap | **Fine-tune 2 tahap** |
|---|---|---|---|
| mAP50 | 0,304 | 0,787 | **0,827** |
| mAP50-95 | 0,209 | 0,523 | **0,569** |
| Precision | 0,617 | 0,779 | **0,795** |
| Recall | 0,279 | 0,752 | **0,787** |

Yang paling berarti untuk produk adalah **recall**: 0,279 → 0,787. Model generik
hanya menemukan 28% barang di rak; setelah fine-tune menjadi 79%. Barang yang
tidak terdeteksi tidak akan pernah terhitung, sehingga recall-lah yang membatasi
akurasi opname — bukan mAP.

**Tahap 1 terbukti menyumbang, bukan sekadar cerita kepatuhan.** Fine-tune yang
berangkat dari checkpoint SKU-110K mengungguli fine-tune langsung dari COCO
sebesar +0,040 mAP50 dan +0,034 recall, dengan dataset, jumlah epoch, dan
seluruh hyperparameter yang identik. Selisih itu satu-satunya yang berbeda:
titik awal bobot.

### 4.7 Skema data

```mermaid
erDiagram
    products ||--o{ product_embeddings : "galeri pengenalan"
    products ||--o{ stock_ledger : "riwayat qty"
    products ||--o{ scan_items : "hasil deteksi"
    scans ||--o{ scan_items : ""
    scans ||--o{ unknown_crops : "belum dikenali"
    products ||--o{ unknown_crops : "setelah diberi nama"

    products {
        int id
        text nama
        int harga_modal
        int harga_jual
        int stok_minimum
        blob embedding
    }
    scans {
        int id
        text tanggal
        text tipe
        text terapkan_pada
    }
    scan_items {
        int qty_terdeteksi
        real confidence_avg
        text expired_terdekat
        int qty_expired
    }
    stock_ledger {
        int qty_tercatat
        text sumber
        text alasan
    }
```

**Keputusan: stok disimpan sebagai buku besar (ledger), bukan satu kolom
angka.** Angka selisih tidak bermakna tanpa angka pembanding yang tercatat
beserta asal-usulnya. Ledger membuat setiap perubahan stok dapat ditelusuri —
berasal dari opname yang mana, atau penyesuaian manual dengan alasan apa.

Penerapan hasil opname ke ledger berjalan dalam **satu transaksi atomik** dengan
penjagaan *compare-and-set*, sehingga dua permintaan bersamaan tidak dapat
menerapkan opname yang sama dua kali.

---

## 5. Metode Pendukung Pengambilan Keputusan

Bagian ini merangkum bagaimana keputusan diambil, bukan sekadar apa yang
diputuskan.

### 5.1 Keputusan yang diubah setelah analisis

| Keputusan awal | Diubah menjadi | Dasar perubahan |
|---|---|---|
| Rata-ratakan vektor enrollment dengan vektor scan | Galeri banyak-vektor, ambil similarity tertinggi | Analisis: rata-rata dua kondisi yang sangat berbeda menghasilkan vektor yang tidak mirip keduanya |
| Hitung per track ID | Tambah line-crossing sebagai lapis ketiga | Uji: ID pecah membuat satu barang terhitung dua kali |
| Video sebagai mode utama | Foto sebagai mode utama | Analisis biaya dan kelas kesalahan: satu foto = satu deteksi per barang, tidak ada masalah ID pecah |
| Ambil foto dataset di toko grosir | Ambil di warung Madura | Analisis domain: model dasar sudah dilatih pada rak rapi; mengambil data di lingkungan rapi membuka jurang domain kedua |
| Bangun export dan analitik tambahan | Dibatalkan | Ruang lingkup MVP harus tetap pada alur inti |

### 5.2 Kegagalan yang terdokumentasi

Dokumentasi tim menyimpan **alasan penolakan**, bukan hanya keputusan yang
diterima. Dua contoh yang berdampak nyata:

**Konflik semantik antar cabang.** Dua cabang yang masing-masing lulus pengujian
dapat menghasilkan kegagalan setelah digabung, karena konfliknya bersifat makna,
bukan tekstual — git melaporkan penggabungan bersih, tetapi pengujian gabungan
gagal. Terjadi dua kali sebelum akhirnya dijadikan aturan tertulis: **cabang yang
menyentuh berkas sama wajib menggabungkan cabang utama dan menjalankan pengujian
sebelum digabung.** Aturan turunannya: uji penjaga harus menguji **pola**, bukan
keberadaan kata.

**Regresi yang lahir dari perbaikan.** Pada satu unit, perbaikan atas kondisi
balapan justru menimbulkan cacat baru berupa tombol yang tidak pernah aktif
kembali. Ditemukan pada putaran review ketiga. Ini menjadi alasan mengapa
peninjauan dilakukan berlapis dan hasilnya ditulis ke dokumen rencana, bukan
dibiarkan hilang di percakapan.

**Kerusakan label yang tidak menimbulkan satu pun pesan galat.** Roboflow
menyediakan *Smart Polygon* untuk mengikuti lekuk barang, dan pelabel kami
memakainya untuk bentuk sulit — kerupuk gantung, renceng melengkung — sambil
tetap memakai kotak biasa untuk dus. Wajar, dan dokumentasi internal kami
sendiri sempat menyatakan pencampuran itu tidak bermasalah.

Ternyata bermasalah, di tempat yang tidak terlihat. Ekspor format YOLO menulis
koordinat poligon apa adanya, lalu pustaka pelatihan memeriksa bentuk label
**per berkas, bukan per baris**: satu baris poligon membuat seluruh baris di
berkas itu dibaca sebagai poligon. Baris kotak `cls cx cy w h` ditafsirkan
sebagai dua titik — titik pusat dan ukuran diperlakukan sebagai dua sudut —
sehingga kotaknya tidak lagi berhubungan dengan barang aslinya.

```mermaid
flowchart TB
    A["Pelabel memakai Smart Polygon<br/>untuk barang berlekuk"] --> B["Satu foto berisi<br/>poligon DAN kotak"]
    B --> C["Ekspor YOLO menulis<br/>koordinat poligon apa adanya"]
    C --> D{"Pustaka melatih:<br/>ada baris > 6 kolom<br/>di berkas ini?"}
    D -->|"ya"| E["SELURUH baris dibaca<br/>sebagai poligon"]
    E --> F["Baris kotak jadi<br/>kotak sampah"]
    F --> G["Tidak ada galat.<br/>Training selesai normal,<br/>kurva terbentuk"]
    G --> H["Model diam-diam lebih buruk"]
    D -->|"tidak"| I["Dibaca benar"]
```

Diukur pada gabungan ekspor kami: dari **11.779 anotasi**, 3.751 berbentuk
poligon dan **2.339 kotak — 19,9% dari seluruh anotasi — berada di 116 berkas
campuran** dan akan rusak. Berkas yang isinya seragam, semua kotak atau semua
poligon, justru aman; yang mematikan adalah pencampuran di dalam satu foto.

Temuan ini menghasilkan langkah normalisasi wajib sebelum pelatihan, dan
koreksi pada panduan internal yang sebelumnya keliru. Kami mencantumkannya di
sini karena kegagalan jenis ini — yang tidak memunculkan galat, tidak
menggagalkan pengujian, dan hanya menyisakan model yang lebih buruk tanpa sebab
yang jelas — adalah kegagalan yang paling mahal dalam proyek pembelajaran mesin,
dan satu-satunya pertahanannya adalah memeriksa data, bukan menunggu peringatan.

### 5.3 Parameter yang dapat disetel, dan cara menyetelnya

| Parameter | Nilai berlaku | Gejala bila terlalu rendah | Gejala bila terlalu tinggi |
|---|---|---|---|
| Ambang pencocokan | **0,85** (diukur) | Barang asing disangka produk terdaftar | Banyak item "belum dikenali" |
| Umur minimum track | 3 frame | Noise ikut terhitung | Barang yang sekilas terlihat terlewat |
| Interval pengambilan embedding | tiap 5 frame | Lambat | Suara terlalu sedikit untuk memilih label |

#### Ambang pencocokan: dari tebakan menjadi pengukuran

Nilai 0,75 yang dipakai di awal tidak pernah divalidasi — dasarnya hanya tiga
kasus tunggal, dan itu anekdot. Kami mengukurnya ulang pada **12 produk dan 104
foto** dengan dua uji terpisah: *leave-one-out* untuk kemampuan mengenali, dan
*leave-one-product-out* untuk kemampuan menolak.

![Trade-off ambang pencocokan CLIP](gambar/04-ambang-clip.png)

Pengukuran itu memperlihatkan hal yang tidak terlihat sebelumnya: **pada 0,75,
satu dari tiga barang yang belum didaftarkan disangka produk lain** — 33 dari
104. Di laporan opname, kesalahan itu muncul sebagai barang dengan nama yang
salah. Ini jenis kesalahan paling merusak, karena hasilnya terbaca meyakinkan
dan tidak meninggalkan tanda apa pun bahwa ada yang keliru.

Ambang mana yang terbaik bergantung pada komposisi rak:

| Rasio barang asing : terdaftar | Ambang terbaik |
|---|---|
| 1 : 1 | 0,80 |
| **3 : 1 (rak warung nyata)** | **0,85** |

Warung mendaftarkan puluhan produk sementara raknya memuat ratusan barang,
sehingga barang yang belum terdaftar jauh lebih banyak. **Keputusan: naik ke
0,85.** Konsekuensinya diterima secara sadar — pengenalan produk terdaftar turun
dari 0,933 ke 0,673, ditukar dengan kesalahan penamaan yang turun dari 33 kasus
menjadi nol. Bagi pemilik warung, "belum dikenali" adalah barang yang tinggal
diberi nama sekali; "salah nama" adalah angka rupiah yang salah tanpa ia sadari.

### 5.4 Cara memverifikasi klaim

Klaim modularitas diverifikasi mesin, bukan pernyataan: pipeline CI memasang
lingkungan **tanpa** tumpukan torch dan menjalankan seluruh test cepat pada
setiap pull request. Pipeline terpisah **membangun image kontainer dan menguji
aplikasinya benar-benar melayani permintaan**, sehingga klaim "dapat dijalankan
dengan satu perintah" tidak bergantung pada laptop siapa pun.

---

## 6. Kesiapan dan Cara Menjalankan

Seluruh aplikasi berjalan lokal dengan satu perintah:

```bash
docker compose up --build
```

🔴 **Hasil uji lapangan** — diisi setelah pengujian di warung:

| Pengukuran | Hasil |
|---|---|
| Jumlah barang yang didaftarkan | ⟨…⟩ |
| Akurasi hitungan dibanding hitung manual | ⟨…⟩ |
| Waktu opname satu rak | ⟨…⟩ |
| Tanggapan pemilik warung | ⟨…⟩ |

---

## 7. Kesimpulan

StokLens menjawab persoalan yang nyata dan terukur: pemilik warung tidak
mengetahui nilai stok dan angka kehilangannya karena menghitung manual terlalu
mahal. Pendekatan yang dipilih — deteksi produk pada foto rak, pengenalan
berbasis pembandingan embedding tanpa retraining, dan pelaporan selisih dalam
rupiah — memungkinkan opname dilakukan dengan perangkat yang sudah dimiliki
pemilik warung.

Tiga hal yang kami anggap paling menentukan:

1. **Berjalan lokal sepenuhnya.** Biaya per-scan nol dan data tidak pernah keluar
   dari toko — pembeda terhadap solusi yang bergantung pada layanan AI berbayar.
2. **Memperbaiki diri dari pemakaian.** Setiap barang yang gagal dikenali lalu
   diberi nama pengguna memperkaya galeri dalam kondisi yang identik dengan
   kondisi pemakaian nyata.
3. **Keputusan berbasis analisis, termasuk yang dikoreksi.** Beberapa keputusan
   penting justru merupakan pembatalan rencana awal setelah analisis menunjukkan
   rencana itu keliru — ambang pencocokan yang dinaikkan setelah diukur, dan
   panduan pelabelan internal yang dikoreksi setelah ditemukan merusak 20%
   anotasi tanpa memunculkan galat.

Fine-tune dua tahap sudah selesai dan terukur pada warung yang seluruhnya
ditahan dari data latih: **mAP50 0,304 → 0,827** dan **recall 0,279 → 0,787**.
Recall adalah angka yang membatasi akurasi opname, karena barang yang tidak
terdeteksi tidak akan pernah terhitung.

🔴 Angka uji lapangan di warung melengkapi proposal ini sebelum pengumpulan.

---

## Lampiran A — Ringkasan Keputusan Teknis

| # | Keputusan | Alasan singkat |
|---|---|---|
| 1 | SQLite satu berkas | Skala warung; satu perintah jalan; cadangan = salin berkas |
| 2 | CLIP zero-shot, bukan pengklasifikasi terlatih | Barang baru tidak boleh memerlukan retraining |
| 3 | Satu kelas `produk` pada detektor | Pelabelan cepat; barang baru tidak perlu pelabelan ulang |
| 4 | Mode foto sebagai mode utama | Satu deteksi = satu barang; lebih murah; OCR lebih tajam |
| 5 | Anti dobel-hitung berlapis tiga | Tidak ada satu mekanisme yang cukup |
| 6 | Galeri banyak-vektor, bukan rata-rata | Rata-rata dua kondisi berbeda tidak mirip keduanya |
| 7 | Vektor dihitung saat scan | Endpoint pemberian nama bebas CLIP, cepat, dapat diuji |
| 8 | Ledger, bukan kolom angka | Selisih tidak bermakna tanpa pembanding yang tertelusur |
| 9 | Pre-train dua tahap | Dataset sendiri terlalu kecil untuk bentuk umum rak |
| 10 | Foto dataset dari warung, bukan grosir | Menghindari jurang domain kedua |
| 11 | Satu sachet = satu kotak pada renceng | Menyamakan dengan cara warung menghitung stok |
| 12 | Menolak scraping marketplace | Melanggar ketentuan layanan dan jenis datanya salah |
