/* Logika halaman Laporan: daftar semua scan (terbaru dulu), tap -> detail. */

/**
 * Format tanggal ISO jadi format Indonesia singkat. Kalau gagal parse, kembalikan aslinya.
 * @param {string} iso
 * @returns {string}
 */
function formatTanggalScan(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function kartuScan(s) {
  /* baris meta: lokasi dan shrinkage dipisah " · " supaya tidak menempel */
  const meta = [];
  if (s.lokasi_rak) {
    meta.push('<span class="laporan-lokasi">' + escapeHtml(s.lokasi_rak) + "</span>");
  }
  if (s.total_shrinkage_rp > 0) {
    meta.push(
      '<span class="laporan-shrinkage accent-neg">Shrinkage: ' +
        rp(s.total_shrinkage_rp) +
        "</span>"
    );
  }
  return (
    '<a class="card laporan-card" href="/ui/laporan/' +
    s.id +
    '"><div class="laporan-card-atas"><span class="laporan-tanggal">' +
    formatTanggalScan(s.tanggal) +
    '</span><span class="badge">' +
    escapeHtml(s.tipe) +
    "</span></div>" +
    (meta.length
      ? '<div class="laporan-card-meta">' +
        meta.join('<span class="laporan-sep" aria-hidden="true">·</span>') +
        "</div>"
      : "") +
    "</a>"
  );
}

const PESAN_BELUM_ADA_OPNAME =
  '<div class="empty-state"><p>Belum ada opname</p>' +
  '<a class="btn btn-cta" href="/ui/opname">Mulai opname</a></div>';

function tampilkanErrorMuat() {
  const kontainer = document.getElementById("daftar-laporan");
  kontainer.innerHTML =
    '<div class="card error-state"><p>Gagal memuat</p>' +
    '<button type="button" class="btn" id="coba-lagi">Coba lagi</button></div>';
  document.getElementById("coba-lagi").addEventListener("click", muatLaporan);
}

async function muatLaporan() {
  let daftar;
  try {
    daftar = await api("/api/scans");
  } catch (e) {
    tampilkanErrorMuat();
    return;
  }
  const kontainer = document.getElementById("daftar-laporan");
  kontainer.innerHTML = daftar.length
    ? daftar.map(kartuScan).join("")
    : PESAN_BELUM_ADA_OPNAME;
}

document.addEventListener("DOMContentLoaded", muatLaporan);
