/* Komponen render laporan opname bersama, dipakai opname_manual/foto/video +
   laporan_detail. Butuh app.js (rp, escapeHtml, api, toast) dimuat lebih dulu. */

const IKON_PANAH_NAIK =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>';

const IKON_PANAH_TURUN =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>';

const IKON_TUTUP_SHEET =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

/**
 * Format tanggal ISO jadi format Indonesia singkat. Kalau gagal parse, kembalikan aslinya.
 * @param {string} iso
 * @returns {string}
 */
function formatTanggalLaporan(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function badgeSelisih(selisih) {
  const kelas = selisih < 0 ? "badge-neg" : "badge-pos";
  const ikon = selisih < 0 ? IKON_PANAH_TURUN : IKON_PANAH_NAIK;
  const teks = (selisih > 0 ? "+" : "") + selisih;
  return '<span class="badge ' + kelas + '">' + ikon + teks + "</span>";
}

function kartuItemLaporan(item) {
  return (
    '<div class="card laporan-item">' +
    '<div class="laporan-item-atas"><span class="laporan-item-nama">' +
    escapeHtml(item.nama) +
    "</span>" +
    badgeSelisih(item.selisih) +
    "</div>" +
    '<div class="laporan-item-baris"><span>Tercatat: <b class="tabular">' +
    item.qty_tercatat +
    '</b></span><span>Terdeteksi: <b class="tabular">' +
    item.qty_terdeteksi +
    "</b></span></div>" +
    '<div class="laporan-item-sub' +
    (item.shrinkage_rp > 0 ? " accent-neg" : "") +
    '">Shrinkage: ' +
    rp(item.shrinkage_rp) +
    "</div>" +
    (item.expired_terdekat
      ? '<div class="laporan-item-sub accent-neg">Kedaluwarsa terdekat: ' +
        formatTanggalLaporan(item.expired_terdekat) +
        " (" +
        item.qty_expired +
        " unit)</div>"
      : "") +
    "</div>"
  );
}

function kartuTotalsLaporan(report) {
  return (
    '<section class="kpi-grid" aria-label="Ringkasan opname">' +
    '<div class="card kpi-card"><span class="kpi-label">Nilai stok</span>' +
    '<span class="kpi-angka tabular">' +
    rp(report.total_nilai_rp) +
    "</span></div>" +
    '<div class="card kpi-card"><span class="kpi-label">Shrinkage</span>' +
    '<span class="kpi-angka tabular accent-neg">' +
    rp(report.total_shrinkage_rp) +
    "</span></div>" +
    '<div class="card kpi-card"><span class="kpi-label">Rugi expired</span>' +
    '<span class="kpi-angka tabular accent-neg">' +
    rp(report.total_rugi_expired_rp) +
    "</span></div>" +
    "</section>"
  );
}

/**
 * Render laporan opname (totals + item) ke containerEl.
 * @param {HTMLElement} containerEl
 * @param {object} report - {items, total_nilai_rp, total_shrinkage_rp, total_rugi_expired_rp}
 * @param {{scanId?: number|string, tampilkanTerapkan?: boolean, sudahDiterapkan?: boolean}} [opts]
 */
function renderReport(containerEl, report, opts) {
  opts = opts || {};

  const items = report.items.length
    ? report.items.map(kartuItemLaporan).join("")
    : '<p class="empty-state-kecil">Tidak ada item</p>';

  const tombolHtml = opts.tampilkanTerapkan
    ? '<button type="button" class="btn btn-cta btn-full" id="tombol-terapkan-opname"' +
      (opts.sudahDiterapkan ? " disabled>Sudah diterapkan" : ">Terapkan ke buku stok") +
      "</button>"
    : "";

  containerEl.innerHTML =
    kartuTotalsLaporan(report) +
    '<div class="laporan-item-list">' +
    items +
    "</div>" +
    tombolHtml;

  if (opts.scanId) muatBelumDikenali(containerEl, opts.scanId);

  if (!opts.tampilkanTerapkan || opts.sudahDiterapkan) return;

  const tombol = document.getElementById("tombol-terapkan-opname");
  tombol.addEventListener("click", async () => {
    if (!confirm("Terapkan hasil opname ini ke buku stok?")) return;
    tombol.disabled = true;
    /* fetch mentah (bukan api()) supaya 409 "sudah diterapkan" bisa dibedakan
       dari error lain: 409 = tombol tetap disabled, error lain = boleh coba lagi */
    let res;
    try {
      res = await fetch("/api/opname/" + opts.scanId + "/terapkan", { method: "POST" });
    } catch (e) {
      toast(PESAN_OFFLINE, false);
      tombol.disabled = false;
      return;
    }
    if (res.status === 409) {
      let detail = "Opname ini sudah diterapkan";
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch (e) {
        /* respons bukan JSON, pakai pesan default */
      }
      toast(detail, false);
      tombol.textContent = "Sudah diterapkan";
      return;
    }
    if (!res.ok) {
      toast("Gagal menerapkan hasil opname", false);
      tombol.disabled = false;
      return;
    }
    toast("Hasil opname diterapkan ke buku stok");
    tombol.textContent = "Sudah diterapkan";
  });
}

/* ---------- Belum dikenali (crop hasil scan yang belum bisa dicocokkan) ---------- */

function kartuCropTakDikenali(crop) {
  return (
    '<div class="thumb-unknown" data-crop-id="' +
    crop.id +
    '"><img src="' +
    escapeHtml(crop.crop_url) +
    '" alt=""><button type="button" class="thumb-tanya" data-crop-id="' +
    crop.id +
    '">Ini barang apa?</button></div>'
  );
}

/**
 * Hapus satu kartu crop dari grid setelah berhasil di-assign/jadi produk baru.
 * Kalau grid jadi kosong, seluruh section "Belum dikenali" ikut disembunyikan.
 * @param {HTMLElement} section
 * @param {number} cropId
 * @param {string} nama
 */
function hapusCropDariGrid(section, cropId, nama) {
  const kartu = section.querySelector('.thumb-unknown[data-crop-id="' + cropId + '"]');
  if (kartu) kartu.remove();
  toast("Ditambahkan ke galeri " + nama);
  if (!section.querySelector(".thumb-unknown")) section.remove();
}

/**
 * Fetch daftar crop belum dikenali untuk satu scan; kalau ada, tambahkan section
 * "Belum dikenali" di bawah laporan. List kosong = tidak tampilkan apa-apa (bukan
 * fitur inti, tidak perlu toast). Request gagal (network/non-2xx) DIBEDAKAN dari
 * list kosong lewat console.error, supaya kegagalan diam-diam tidak terlihat sama
 * dengan "memang tidak ada unknown crop" — konsekuensi yang diterima: item baru
 * kelihatan lagi setelah reload halaman, bukan retry otomatis.
 * @param {HTMLElement} containerEl
 * @param {number|string} scanId
 */
async function muatBelumDikenali(containerEl, scanId) {
  let crops;
  try {
    const res = await fetch("/api/scans/" + scanId + "/unknown");
    if (!res.ok) {
      console.error("Gagal memuat daftar belum dikenali, status:", res.status);
      return;
    }
    crops = await res.json();
  } catch (e) {
    console.error("Gagal memuat daftar belum dikenali:", e);
    return;
  }
  if (!crops || crops.length === 0) return;

  const section = document.createElement("section");
  section.className = "belum-dikenali-section";
  section.innerHTML =
    '<div class="section-head"><h2>Belum dikenali</h2></div>' +
    '<div class="thumbnail-grid">' +
    crops.map(kartuCropTakDikenali).join("") +
    "</div>";
  containerEl.appendChild(section);

  section.querySelectorAll(".thumb-tanya").forEach((btn) => {
    const cropId = Number(btn.dataset.cropId);
    btn.addEventListener("click", () => {
      /* Cegah dobel-tap buka sheet dua kali (dua GET /api/products) sebelum kartu
         sempat hilang dari grid. Dikembalikan aktif lagi di tutupSheet(). */
      btn.disabled = true;
      bukaSheetTakDikenali(cropId, (nama) => hapusCropDariGrid(section, cropId, nama), btn);
    });
  });
}

/* ---------- Sheet "Ini barang apa?" (pilih produk existing atau buat baru) ---------- */

let sheetCropId = null;
let sheetSelesai = null;
let sheetProdukList = [];
let sheetPemicu = null;
/* Naik tiap kali sheet dibuka. Dipakai request in-flight (assign/produk-baru/muat
   produk) untuk tahu apakah sheet sudah "dipakai ulang" buat crop lain sebelum
   request itu selesai — kalau iya, no-op (jangan tutup sheet orang lain, jangan
   panggil callback punya crop yang salah). Lihat catatan review Unit 4. */
let sheetGenerasi = 0;

function daftarFokusableSheet() {
  const panel = document.querySelector("#sheet-backdrop .sheet-panel");
  if (!panel) return [];
  return Array.from(panel.querySelectorAll("button, input")).filter(
    (el) => !el.disabled && el.offsetParent !== null
  );
}

function sheetKeydownHandler(ev) {
  if (ev.key === "Escape") {
    tutupSheet();
    return;
  }
  if (ev.key !== "Tab") return;
  const fokusable = daftarFokusableSheet();
  if (fokusable.length === 0) return;
  const pertama = fokusable[0];
  const terakhir = fokusable[fokusable.length - 1];
  if (ev.shiftKey && document.activeElement === pertama) {
    ev.preventDefault();
    terakhir.focus();
  } else if (!ev.shiftKey && document.activeElement === terakhir) {
    ev.preventDefault();
    pertama.focus();
  }
}

function tutupSheet() {
  const backdrop = document.getElementById("sheet-backdrop");
  if (backdrop) backdrop.classList.add("hidden");
  document.removeEventListener("keydown", sheetKeydownHandler);
  /* Kembalikan fokus ke tombol "Ini barang apa?" yang membuka sheet ini, dan
     aktifkan lagi (lihat guard dobel-tap di muatBelumDikenali). Kalau assign/
     produk-baru sukses, kartunya akan langsung dihapus lagi sesudah ini oleh
     hapusCropDariGrid() — fokus sebentar ke elemen yang mau dibuang tidak masalah,
     browser otomatis pindahkan fokus ke <body>. */
  if (sheetPemicu) {
    if ("disabled" in sheetPemicu) sheetPemicu.disabled = false;
    if (typeof sheetPemicu.focus === "function") sheetPemicu.focus();
  }
  sheetPemicu = null;
}

function renderSheetProdukList(kata) {
  const kontainer = document.getElementById("sheet-produk-list");
  const hasil = kata
    ? sheetProdukList.filter((p) => p.nama.toLowerCase().includes(kata))
    : sheetProdukList;
  kontainer.innerHTML = hasil.length
    ? hasil
        .map(
          (p) =>
            '<button type="button" class="btn btn-full sheet-produk-btn" data-product-id="' +
            p.id +
            '">' +
            escapeHtml(p.nama) +
            "</button>"
        )
        .join("")
    : '<p class="empty-state-kecil">Barang tidak ditemukan</p>';
  kontainer.querySelectorAll(".sheet-produk-btn").forEach((btn) => {
    btn.addEventListener("click", () => pilihProdukExisting(Number(btn.dataset.productId)));
  });
}

async function pilihProdukExisting(productId) {
  /* Tangkap cropId/selesai/generasi SEBELUM await — sheet bisa dipakai ulang buat
     crop lain sementara request ini masih jalan (lihat sheetGenerasi di atas). */
  const cropId = sheetCropId;
  const selesai = sheetSelesai;
  const generasi = sheetGenerasi;
  const produk = sheetProdukList.find((p) => p.id === productId);

  const tombolProduk = Array.from(
    document.querySelectorAll("#sheet-produk-list .sheet-produk-btn")
  );
  tombolProduk.forEach((b) => (b.disabled = true));

  try {
    await api("/api/unknown/" + cropId + "/assign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId }),
    });
  } catch (e) {
    /* toast error sudah tampil dari api(); sheet tetap terbuka supaya bisa coba
       lagi. Kalau generasi sudah beda, tombol-tombol ini sudah tidak relevan lagi
       (sheet sedang menampilkan crop lain) — aman dibiarkan disabled/dibuang. */
    if (generasi === sheetGenerasi) tombolProduk.forEach((b) => (b.disabled = false));
    return;
  }
  if (generasi !== sheetGenerasi) return; /* sheet sudah dipakai untuk crop lain */
  tutupSheet();
  if (selesai) selesai(produk ? produk.nama : "");
}

async function kirimProdukBaru(ev) {
  ev.preventDefault();
  const cropId = sheetCropId;
  const selesai = sheetSelesai;
  const generasi = sheetGenerasi;

  const errorNama = document.getElementById("sheet-error-nama");
  const errorHargaModal = document.getElementById("sheet-error-harga-modal");
  errorNama.classList.add("hidden");
  errorHargaModal.classList.add("hidden");

  const nama = document.getElementById("sheet-nama-baru").value.trim();
  if (!nama) {
    errorNama.classList.remove("hidden");
    return;
  }

  const hargaModal = angka(document.getElementById("sheet-harga-modal-baru").value);
  if (isNaN(hargaModal) || hargaModal < 1) {
    errorHargaModal.classList.remove("hidden");
    return;
  }

  const body = { nama, harga_modal: hargaModal };
  const hargaJualRaw = document.getElementById("sheet-harga-jual-baru").value.trim();
  if (hargaJualRaw) {
    const hargaJual = angka(hargaJualRaw);
    if (!isNaN(hargaJual)) body.harga_jual = hargaJual;
  }

  const tombol = document.getElementById("sheet-submit-baru");
  tombol.disabled = true;
  try {
    await api("/api/unknown/" + cropId + "/produk-baru", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    /* toast error sudah tampil dari api(); sheet tetap terbuka supaya bisa coba lagi */
    if (generasi === sheetGenerasi) tombol.disabled = false;
    return;
  }
  if (generasi !== sheetGenerasi) return; /* sheet sudah dipakai untuk crop lain */
  tombol.disabled = false;
  tutupSheet();
  if (selesai) selesai(nama);
}

/**
 * Bangun elemen sheet sekali (lazy singleton), pasang semua listener sekali.
 * @returns {HTMLElement} elemen backdrop
 */
function pastikanSheetEl() {
  const existing = document.getElementById("sheet-backdrop");
  if (existing) return existing;

  const backdrop = document.createElement("div");
  backdrop.id = "sheet-backdrop";
  backdrop.className = "sheet-backdrop hidden";
  backdrop.innerHTML =
    '<div class="sheet-panel" role="dialog" aria-modal="true" aria-label="Ini barang apa?">' +
    '<div class="sheet-head"><h2>Ini barang apa?</h2>' +
    '<button type="button" class="sheet-close" id="sheet-close" aria-label="Tutup">' +
    IKON_TUTUP_SHEET +
    "</button></div>" +
    '<div class="search-wrap"><label for="sheet-cari">Cari barang</label>' +
    '<input type="search" class="search-input" id="sheet-cari" placeholder="Cari nama barang"></div>' +
    '<div class="produk-list" id="sheet-produk-list"></div>' +
    '<button type="button" class="btn btn-full" id="sheet-toggle-baru">Barang baru</button>' +
    '<form id="sheet-form-baru" class="hidden">' +
    '<div class="field"><label for="sheet-nama-baru">Nama</label>' +
    '<input type="text" id="sheet-nama-baru" required>' +
    '<p class="field-error hidden" id="sheet-error-nama">Nama wajib diisi</p></div>' +
    '<div class="field"><label for="sheet-harga-modal-baru">Harga modal</label>' +
    '<input type="text" inputmode="numeric" id="sheet-harga-modal-baru">' +
    '<p class="field-error hidden" id="sheet-error-harga-modal">Harga modal minimal Rp1</p></div>' +
    '<div class="field"><label for="sheet-harga-jual-baru">Harga jual (opsional)</label>' +
    '<input type="text" inputmode="numeric" id="sheet-harga-jual-baru"></div>' +
    '<button type="submit" class="btn btn-cta btn-full" id="sheet-submit-baru">Simpan barang baru</button>' +
    "</form></div>";
  document.body.appendChild(backdrop);

  backdrop.addEventListener("click", (ev) => {
    if (ev.target === backdrop) tutupSheet();
  });
  document.getElementById("sheet-close").addEventListener("click", tutupSheet);
  document.getElementById("sheet-cari").addEventListener("input", (ev) => {
    renderSheetProdukList(ev.target.value.trim().toLowerCase());
  });
  document.getElementById("sheet-toggle-baru").addEventListener("click", () => {
    document.getElementById("sheet-form-baru").classList.toggle("hidden");
  });
  document.getElementById("sheet-form-baru").addEventListener("submit", kirimProdukBaru);

  return backdrop;
}

/**
 * Buka sheet untuk memberi nama satu crop tak dikenali.
 * @param {number} cropId
 * @param {(nama: string) => void} onSelesai - dipanggil setelah assign/produk-baru sukses
 * @param {HTMLElement} [pemicuEl] - elemen yang men-trigger buka (buat kembalikan fokus)
 */
async function bukaSheetTakDikenali(cropId, onSelesai, pemicuEl) {
  const backdrop = pastikanSheetEl();
  const generasi = ++sheetGenerasi;
  sheetCropId = cropId;
  sheetSelesai = onSelesai;
  sheetPemicu = pemicuEl || document.activeElement;

  document.getElementById("sheet-cari").value = "";
  document.getElementById("sheet-form-baru").classList.add("hidden");
  document.getElementById("sheet-form-baru").reset();
  document.getElementById("sheet-error-nama").classList.add("hidden");
  document.getElementById("sheet-error-harga-modal").classList.add("hidden");
  document.getElementById("sheet-produk-list").innerHTML = "";

  backdrop.classList.remove("hidden");
  document.addEventListener("keydown", sheetKeydownHandler);
  document.getElementById("sheet-cari").focus();

  let produk;
  try {
    produk = await api("/api/products");
  } catch (e) {
    produk = [];
  }
  if (generasi !== sheetGenerasi) return; /* sheet sudah dipakai untuk crop lain */
  sheetProdukList = produk;
  renderSheetProdukList("");
}
