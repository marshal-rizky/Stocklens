/* Logika halaman Tambah Barang: form enrollment + preview foto + margin live. */

const IKON_X =
  '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
  'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
  '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';

/* Tombol hapus dibungkus <span> visual kecil di dalam target sentuh 48px penuh
   (lihat .thumb-remove / .thumb-remove-visual di app.css). */

let fotoFiles = [];

/**
 * Hitung & tampilkan margin % live di bawah field harga jual.
 */
function perbaruiMargin() {
  const modal = parseInt(document.getElementById("input-harga-modal").value, 10);
  const jualRaw = document.getElementById("input-harga-jual").value.trim();
  const hint = document.getElementById("margin-hint");

  if (!jualRaw || isNaN(modal) || modal <= 0) {
    hint.textContent = "—";
    hint.classList.remove("accent-pos", "accent-neg");
    return;
  }
  const jual = parseInt(jualRaw, 10);
  if (isNaN(jual)) {
    hint.textContent = "—";
    hint.classList.remove("accent-pos", "accent-neg");
    return;
  }
  const pct = ((jual - modal) / modal) * 100;
  hint.textContent = "Margin " + pct.toFixed(1).replace(".", ",") + "%";
  hint.classList.toggle("accent-pos", pct >= 0);
  hint.classList.toggle("accent-neg", pct < 0);
}

/**
 * Render grid thumbnail dari fotoFiles, masing-masing dengan tombol hapus.
 */
function renderThumbnail() {
  const grid = document.getElementById("thumbnail-grid");
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

async function kirimForm(ev) {
  ev.preventDefault();

  const errorFoto = document.getElementById("error-foto");
  if (fotoFiles.length === 0) {
    errorFoto.classList.remove("hidden");
    return;
  }
  errorFoto.classList.add("hidden");

  const tombol = document.getElementById("tombol-simpan");
  const teksAsli = tombol.textContent;
  tombol.disabled = true;
  tombol.innerHTML =
    '<span class="spinner" aria-hidden="true"></span><span>Menyimpan... (analisis foto ±10 dtk)</span>';

  const fd = new FormData();
  fd.append("nama", document.getElementById("input-nama").value.trim());
  fd.append("harga_modal", document.getElementById("input-harga-modal").value);
  fd.append("qty_awal", document.getElementById("input-stok-awal").value || "0");
  const hargaJual = document.getElementById("input-harga-jual").value.trim();
  if (hargaJual) fd.append("harga_jual", hargaJual);
  fd.append("stok_minimum", document.getElementById("input-stok-minimum").value || "0");
  fotoFiles.forEach((f) => fd.append("fotos", f));

  try {
    await api("/products", { method: "POST", body: fd });
    toast("Barang terdaftar");
    location.href = "/ui/barang";
  } catch (e) {
    /* toast error sudah tampil dari api() */
    tombol.disabled = false;
    tombol.textContent = teksAsli;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("input-harga-modal").addEventListener("input", perbaruiMargin);
  document.getElementById("input-harga-jual").addEventListener("input", perbaruiMargin);

  document.getElementById("tombol-ambil-foto").addEventListener("click", () => {
    document.getElementById("input-foto").click();
  });

  document.getElementById("input-foto").addEventListener("change", (ev) => {
    fotoFiles = fotoFiles.concat(Array.from(ev.target.files));
    ev.target.value = "";
    document.getElementById("error-foto").classList.add("hidden");
    renderThumbnail();
  });

  document.getElementById("form-barang-baru").addEventListener("submit", kirimForm);
});
