/* Logika halaman Opname Video: upload video (SYNCHRONOUS, bisa lama), pilih
   count_mode, kirim ke POST /scans lalu GET /report/{scan_id}, render lewat
   report_view.js. */

const PENJELASAN_COUNT_MODE = {
  line: "Line: video sapuan (sweep), barang dihitung saat menyeberang garis tengah — anti dobel hitung.",
  track: "Track: kamera statis, semua barang yang terlihat cukup lama dihitung.",
};

async function kirimScanVideo() {
  const fileInput = document.getElementById("input-video");
  const errorVideo = document.getElementById("error-video");
  if (!fileInput.files.length) {
    errorVideo.classList.remove("hidden");
    return;
  }
  errorVideo.classList.add("hidden");

  const tombol = document.getElementById("tombol-scan");
  const teksAsli = tombol.textContent;
  tombol.disabled = true;
  tombol.innerHTML =
    '<span class="spinner" aria-hidden="true"></span>' +
    "<span>Memproses video… bisa &gt;1 menit, jangan tutup halaman</span>";

  const fd = new FormData();
  fd.append("video", fileInput.files[0]);
  const lokasi = document.getElementById("input-lokasi-rak").value.trim();
  if (lokasi) fd.append("lokasi_rak", lokasi);
  fd.append("count_mode", document.getElementById("select-count-mode").value);

  let hasilScan;
  try {
    hasilScan = await api("/scans", { method: "POST", body: fd });
  } catch (e) {
    tombol.disabled = false;
    tombol.textContent = teksAsli;
    return;
  }

  let report;
  try {
    report = await api("/report/" + hasilScan.scan_id);
  } catch (e) {
    tombol.disabled = false;
    tombol.textContent = teksAsli;
    return;
  }

  document.getElementById("form-state").classList.add("hidden");
  document.getElementById("laporan-hasil").classList.remove("hidden");
  renderReport(document.getElementById("laporan-container"), report, {
    scanId: hasilScan.scan_id,
    tampilkanTerapkan: true,
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("select-count-mode").addEventListener("change", (ev) => {
    document.getElementById("hint-count-mode").textContent =
      PENJELASAN_COUNT_MODE[ev.target.value];
  });
  document.getElementById("tombol-scan").addEventListener("click", kirimScanVideo);
});
