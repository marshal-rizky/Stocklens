/* Logika halaman Detail Barang: muat data, ubah data, kartu stok, penyesuaian. */

const SUMBER_LABEL = { opname: "Opname", penyesuaian: "Penyesuaian", manual: "Manual" };

let produkSaatIni = null;
let delta = 0;

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

function badgeMargin(marginPct) {
  if (marginPct === null || marginPct === undefined) return "";
  const kelas = marginPct >= 0 ? "badge-pos" : "badge-neg";
  const angka = marginPct.toString().replace(".", ",");
  return '<span class="badge ' + kelas + '">' + angka + "%</span>";
}

function renderHeader(p) {
  document.getElementById("detail-nama").textContent = p.nama;
  document.getElementById("detail-qty").textContent = p.qty;
  document.getElementById("detail-nilai-stok").textContent = rp(p.qty * p.harga_modal);
  document.getElementById("detail-margin-badge").innerHTML = badgeMargin(p.margin_pct);
}

function isiFormEdit(p) {
  document.getElementById("edit-nama").value = p.nama;
  document.getElementById("edit-harga-modal").value = p.harga_modal;
  document.getElementById("edit-harga-jual").value = p.harga_jual ?? "";
  document.getElementById("edit-stok-minimum").value = p.stok_minimum || 0;
}

function renderLedger(ledger) {
  const kontainer = document.getElementById("daftar-ledger");
  if (ledger.length === 0) {
    kontainer.innerHTML = '<p class="empty-state-kecil">Belum ada riwayat</p>';
    return;
  }
  kontainer.innerHTML = ledger
    .map(
      (r) =>
        '<div class="card ledger-item"><div class="ledger-atas">' +
        '<span class="ledger-qty tabular">' +
        r.qty_tercatat +
        '</span><span class="badge">' +
        (SUMBER_LABEL[r.sumber] || r.sumber) +
        "</span></div>" +
        (r.alasan ? '<span class="ledger-alasan">' + escapeHtml(r.alasan) + "</span>" : "") +
        '<span class="ledger-tanggal">' +
        formatTanggal(r.tanggal_update) +
        "</span></div>"
    )
    .join("");
}

function resetStepper() {
  delta = 0;
  document.getElementById("stepper-angka").textContent = "0";
  document.getElementById("tombol-terapkan").disabled = true;
  document.getElementById("error-penyesuaian").classList.add("hidden");
}

function tampilkanState(id) {
  ["state-loading", "state-error", "state-notfound", "state-konten"].forEach((s) => {
    document.getElementById(s).classList.toggle("hidden", s !== id);
  });
}

function renderDetail(p) {
  produkSaatIni = p;
  renderHeader(p);
  isiFormEdit(p);
  renderLedger(p.ledger);
  resetStepper();
  tampilkanState("state-konten");
}

function idProduk() {
  return document.getElementById("detail-barang").dataset.productId;
}

async function muatDetail() {
  tampilkanState("state-loading");
  let res;
  try {
    res = await fetch("/api/products/" + idProduk());
  } catch (e) {
    tampilkanState("state-error");
    return;
  }
  if (res.status === 404) {
    tampilkanState("state-notfound");
    return;
  }
  if (!res.ok) {
    tampilkanState("state-error");
    return;
  }
  renderDetail(await res.json());
}

async function simpanEdit(ev) {
  ev.preventDefault();
  const errorHargaModal = document.getElementById("error-edit-harga-modal");
  errorHargaModal.classList.add("hidden");

  const nama = document.getElementById("edit-nama").value.trim();
  const hargaModal = parseInt(document.getElementById("edit-harga-modal").value, 10);
  if (isNaN(hargaModal) || hargaModal < 1) {
    errorHargaModal.classList.remove("hidden");
    return;
  }
  const hargaJualRaw = document.getElementById("edit-harga-jual").value.trim();
  const stokMinRaw = document.getElementById("edit-stok-minimum").value.trim();

  const patch = {};
  if (nama && nama !== produkSaatIni.nama) patch.nama = nama;
  if (hargaModal !== produkSaatIni.harga_modal) patch.harga_modal = hargaModal;
  if (hargaJualRaw) {
    const hargaJual = parseInt(hargaJualRaw, 10);
    if (!isNaN(hargaJual) && hargaJual !== produkSaatIni.harga_jual) patch.harga_jual = hargaJual;
  }
  if (stokMinRaw) {
    const stokMin = parseInt(stokMinRaw, 10);
    if (!isNaN(stokMin) && stokMin !== (produkSaatIni.stok_minimum || 0)) {
      patch.stok_minimum = stokMin;
    }
  }

  if (Object.keys(patch).length === 0) {
    toast("Tidak ada perubahan");
    return;
  }

  const tombol = document.getElementById("tombol-simpan-edit");
  tombol.disabled = true;
  try {
    await api("/api/products/" + idProduk(), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    toast("Perubahan disimpan");
    await muatDetail();
  } catch (e) {
    /* toast error sudah tampil dari api() */
  } finally {
    tombol.disabled = false;
  }
}

function ubahDelta(diff) {
  delta += diff;
  document.getElementById("stepper-angka").textContent = (delta > 0 ? "+" : "") + delta;
  document.getElementById("tombol-terapkan").disabled = delta === 0;
}

async function terapkanPenyesuaian() {
  const errorEl = document.getElementById("error-penyesuaian");
  errorEl.classList.add("hidden");

  const tombol = document.getElementById("tombol-terapkan");
  tombol.disabled = true;
  let res;
  try {
    res = await fetch("/api/adjustments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: Number(idProduk()), delta, alasan: document.getElementById("select-alasan").value }),
    });
  } catch (e) {
    toast("Tidak bisa terhubung ke server", false);
    tombol.disabled = delta === 0;
    return;
  }
  if (res.status === 400) {
    const body = await res.json();
    errorEl.textContent = body.detail || "Penyesuaian ditolak";
    errorEl.classList.remove("hidden");
    tombol.disabled = false;
    return;
  }
  if (!res.ok) {
    toast("Gagal menerapkan penyesuaian", false);
    tombol.disabled = false;
    return;
  }
  const body = await res.json();
  toast("Stok: " + body.qty_lama + " → " + body.qty_baru);
  await muatDetail();
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("coba-lagi").addEventListener("click", muatDetail);
  document.getElementById("form-edit").addEventListener("submit", simpanEdit);
  document.getElementById("stepper-minus").addEventListener("click", () => ubahDelta(-1));
  document.getElementById("stepper-plus").addEventListener("click", () => ubahDelta(1));
  document.getElementById("tombol-terapkan").addEventListener("click", terapkanPenyesuaian);
  muatDetail();
});
