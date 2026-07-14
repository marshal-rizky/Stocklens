/* Logika halaman Beranda: ambil ringkasan dashboard, isi KPI + peringatan. */

const IKON_CEK =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M20 6 9 17l-5-5"/></svg>';

/**
 * Format tanggal ISO jadi format Indonesia singkat. Kalau gagal parse, kembalikan aslinya.
 * @param {string} iso
 * @returns {string}
 */
function formatTanggal(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

function isiKpi(data) {
  const kpiNilai = document.getElementById("kpi-nilai");
  kpiNilai.querySelector('[data-slot="angka"]').textContent = rp(data.nilai_stok_rp);
  kpiNilai.classList.remove("skeleton");

  const kpiLaba = document.getElementById("kpi-laba");
  kpiLaba.querySelector('[data-slot="angka"]').textContent = rp(data.potensi_laba_rp);
  kpiLaba.classList.remove("skeleton");

  const kpiOpname = document.getElementById("kpi-opname");
  const angkaOpname = kpiOpname.querySelector('[data-slot="angka"]');
  const subOpname = kpiOpname.querySelector('[data-slot="sub"]');
  if (data.scan_terakhir) {
    angkaOpname.textContent = rp(data.scan_terakhir.total_shrinkage_rp);
    subOpname.textContent =
      formatTanggal(data.scan_terakhir.tanggal) + " · " + data.scan_terakhir.tipe;
  } else {
    angkaOpname.textContent = "Belum ada opname";
    subOpname.textContent = "";
  }
  kpiOpname.classList.remove("skeleton");
}

function isiPeringatan(stokMenipis) {
  const kontainer = document.getElementById("peringatan");
  if (stokMenipis.length === 0) {
    kontainer.innerHTML =
      '<p class="peringatan-aman">' + IKON_CEK + "<span>Semua stok aman</span></p>";
    return;
  }
  const items = stokMenipis
    .map(
      (p) =>
        '<a class="card peringatan-item" href="/ui/barang/' +
        p.id +
        '"><span class="nama">' +
        escapeHtml(p.nama) +
        '</span><span class="badge badge-neg">' +
        p.qty +
        "/" +
        p.stok_minimum +
        "</span></a>"
    )
    .join("");
  kontainer.innerHTML = '<div class="peringatan-list">' + items + "</div>";
}

function cekKosongGlobal(data) {
  const kosong =
    data.nilai_stok_rp === 0 &&
    data.stok_menipis.length === 0 &&
    data.scan_terakhir === null;
  document.getElementById("konten-utama").classList.toggle("hidden", kosong);
  document.getElementById("onboarding").classList.toggle("hidden", !kosong);
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    const data = await api("/api/dashboard");
    isiKpi(data);
    isiPeringatan(data.stok_menipis);
    cekKosongGlobal(data);
  } catch (e) {
    /* toast error sudah ditampilkan oleh api() */
  }
});
