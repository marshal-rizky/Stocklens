/* Logika halaman Detail Laporan: muat /report/{scan_id}, render lewat report_view.js. */

function idScanLaporan() {
  return document.getElementById("laporan-detail").dataset.scanId;
}

function tampilkanStateLaporan(id) {
  ["state-loading", "state-error", "laporan-container"].forEach((s) => {
    document.getElementById(s).classList.toggle("hidden", s !== id);
  });
}

async function muatLaporanDetail() {
  tampilkanStateLaporan("state-loading");
  let report;
  try {
    report = await api("/report/" + idScanLaporan());
  } catch (e) {
    tampilkanStateLaporan("state-error");
    return;
  }
  tampilkanStateLaporan("laporan-container");
  renderReport(document.getElementById("laporan-container"), report, {
    scanId: idScanLaporan(),
    tampilkanTerapkan: true,
    /* laporan historis yang sudah pernah diterapkan tidak boleh diterapkan
       ulang (menimpa stok sekarang dengan snapshot basi) */
    sudahDiterapkan: Boolean(report.scan && report.scan.terapkan_pada),
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("coba-lagi").addEventListener("click", muatLaporanDetail);
  muatLaporanDetail();
});
