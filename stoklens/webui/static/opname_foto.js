/* Logika halaman Opname Foto: capture multi-foto + thumbnail grid (pola sama
   dengan barang_baru.js, termasuk revoke objectURL), guided mode opsional,
   kirim ke /api/scans-foto, lalu render laporan lewat report_view.js. */

const IKON_X =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

let fotoFiles = [];

/**
 * Render grid thumbnail dari fotoFiles, masing-masing dengan tombol hapus.
 * Object URL batch sebelumnya di-revoke dulu supaya tidak bocor memori.
 */
function renderThumbnail() {
  const grid = document.getElementById("thumbnail-grid");
  grid.querySelectorAll("img").forEach((img) => URL.revokeObjectURL(img.src));
  grid.innerHTML = fotoFiles
    .map(
      (f, i) =>
        '<div class="thumb"><img src="' +
        URL.createObjectURL(f) +
        '" alt=""><button type="button" class="thumb-remove" data-idx="' +
        i +
        '" aria-label="Hapus foto"><span class="thumb-remove-visual">' +
        IKON_X +
        "</span></button></div>"
    )
    .join("");
  grid.querySelectorAll(".thumb-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      fotoFiles.splice(Number(btn.dataset.idx), 1);
      renderThumbnail();
    });
  });
}

async function muatProdukGuided() {
  try {
    const produk = await api("/api/products");
    const select = document.getElementById("select-guided");
    produk
      .sort((a, b) => a.nama.localeCompare(b.nama, "id"))
      .forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.nama;
        select.appendChild(opt);
      });
  } catch (e) {
    /* guided mode opsional; biarkan kosong kalau daftar produk gagal dimuat */
  }
}

async function kirimScanFoto() {
  const errorFoto = document.getElementById("error-foto");
  if (fotoFiles.length === 0) {
    errorFoto.classList.remove("hidden");
    return;
  }
  errorFoto.classList.add("hidden");

  const tombol = document.getElementById("tombol-scan");
  const teksAsli = tombol.textContent;
  tombol.disabled = true;
  tombol.innerHTML =
    '<span class="spinner" aria-hidden="true"></span><span>Menganalisis foto… (±30 dtk)</span>';

  const fd = new FormData();
  fotoFiles.forEach((f) => fd.append("fotos", f));
  const lokasi = document.getElementById("input-lokasi-rak").value.trim();
  if (lokasi) fd.append("lokasi_rak", lokasi);
  const guided = document.getElementById("select-guided").value;
  if (guided) fd.append("guided_product_id", guided);
  fd.append("read_expiry", "true");

  let hasil;
  try {
    hasil = await api("/api/scans-foto", { method: "POST", body: fd });
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
  muatProdukGuided();

  /* Dua sumber foto: kamera (satu-satu) dan galeri (banyak sekaligus),
     keduanya menambah ke daftar yang sama. */
  function tambahFoto(ev) {
    fotoFiles = fotoFiles.concat(Array.from(ev.target.files));
    ev.target.value = "";
    document.getElementById("error-foto").classList.add("hidden");
    renderThumbnail();
  }

  document.getElementById("tombol-kamera").addEventListener("click", () => {
    document.getElementById("input-foto-kamera").click();
  });
  document.getElementById("tombol-galeri").addEventListener("click", () => {
    document.getElementById("input-foto-galeri").click();
  });
  document.getElementById("input-foto-kamera").addEventListener("change", tambahFoto);
  document.getElementById("input-foto-galeri").addEventListener("change", tambahFoto);

  document.getElementById("tombol-scan").addEventListener("click", kirimScanFoto);
});
