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
