/* Logika halaman Opname Manual: checklist semua produk, stepper qty, kirim
   /api/opname-manual, lalu render laporan lewat report_view.js. */

const IKON_MINUS =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M5 12h14"/></svg>';

const IKON_PLUS =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M5 12h14"/><path d="M12 5v14"/></svg>';

function barisChecklist(p) {
  return (
    '<div class="card checklist-row">' +
    '<div class="checklist-info"><span class="checklist-nama">' +
    escapeHtml(p.nama) +
    '</span><span class="checklist-hint">tercatat: ' +
    p.qty +
    "</span></div>" +
    '<div class="stepper stepper-kecil">' +
    '<button type="button" class="btn stepper-btn" data-id="' +
    p.id +
    '" data-aksi="kurang" aria-label="Kurangi ' +
    escapeHtml(p.nama) +
    '">' +
    IKON_MINUS +
    "</button>" +
    '<input type="text" inputmode="numeric" class="checklist-input tabular" ' +
    'data-id="' +
    p.id +
    '" placeholder="0">' +
    '<button type="button" class="btn stepper-btn" data-id="' +
    p.id +
    '" data-aksi="tambah" aria-label="Tambah ' +
    escapeHtml(p.nama) +
    '">' +
    IKON_PLUS +
    "</button>" +
    "</div></div>"
  );
}

function perbaruiProgress() {
  const inputs = document.querySelectorAll(".checklist-input");
  let terisi = 0;
  inputs.forEach((inp) => {
    if (!isNaN(angka(inp.value))) terisi++;
  });
  document.getElementById("progress-sticky").textContent =
    "Terisi " + terisi + "/" + inputs.length;
  document.getElementById("tombol-hitung").disabled = terisi === 0;
}

function ubahStepperChecklist(id, diff) {
  const input = document.querySelector('.checklist-input[data-id="' + id + '"]');
  const sekarang = angka(input.value);
  const dasar = isNaN(sekarang) ? 0 : sekarang;
  input.value = String(Math.max(0, dasar + diff));
  perbaruiProgress();
}

function tampilkanErrorMuat() {
  document.getElementById("daftar-checklist").innerHTML =
    '<div class="card error-state"><p>Gagal memuat</p>' +
    '<button type="button" class="btn" id="coba-lagi">Coba lagi</button></div>';
  document.getElementById("coba-lagi").addEventListener("click", muatChecklist);
}

async function muatChecklist() {
  let produk;
  try {
    produk = await api("/api/products");
  } catch (e) {
    tampilkanErrorMuat();
    return;
  }

  if (produk.length === 0) {
    document.getElementById("state-kosong").classList.remove("hidden");
    document.getElementById("progress-sticky").classList.add("hidden");
    document.getElementById("tombol-hitung").classList.add("hidden");
    return;
  }

  produk.sort((a, b) => a.nama.localeCompare(b.nama, "id"));
  document.getElementById("daftar-checklist").innerHTML =
    produk.map(barisChecklist).join("");
  perbaruiProgress();
}

async function kirimOpname() {
  const items = [];
  document.querySelectorAll(".checklist-input").forEach((inp) => {
    const v = angka(inp.value);
    if (!isNaN(v)) items.push({ product_id: Number(inp.dataset.id), qty_fisik: v });
  });
  if (items.length === 0) return;

  const lokasi = document.getElementById("input-lokasi-rak").value.trim();
  const tombol = document.getElementById("tombol-hitung");
  const teksAsli = tombol.textContent;
  tombol.disabled = true;
  tombol.textContent = "Menghitung...";

  let hasil;
  try {
    hasil = await api("/api/opname-manual", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, lokasi_rak: lokasi || null, terapkan: false }),
    });
  } catch (e) {
    tombol.disabled = false;
    tombol.textContent = teksAsli;
    return;
  }

  document.getElementById("form-state").classList.add("hidden");
  document.getElementById("laporan-hasil").classList.remove("hidden");
  renderReport(document.getElementById("laporan-container"), hasil.report, {
    scanId: hasil.scan_id,
    tampilkanTerapkan: true,
  });
}

document.addEventListener("DOMContentLoaded", () => {
  muatChecklist();

  document.getElementById("daftar-checklist").addEventListener("click", (ev) => {
    const btn = ev.target.closest(".stepper-btn");
    if (!btn) return;
    ubahStepperChecklist(btn.dataset.id, btn.dataset.aksi === "tambah" ? 1 : -1);
  });
  document.getElementById("daftar-checklist").addEventListener("input", (ev) => {
    if (ev.target.classList.contains("checklist-input")) perbaruiProgress();
  });
  document.getElementById("tombol-hitung").addEventListener("click", kirimOpname);
});
