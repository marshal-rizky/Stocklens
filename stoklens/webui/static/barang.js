/* Logika halaman Barang: ambil daftar produk, render kartu, filter pencarian client-side. */

let semuaProduk = [];

/**
 * Format satu produk jadi kartu HTML.
 * @param {object} p
 * @returns {string}
 */
function kartuProduk(p) {
  const hargaJual = p.harga_jual
    ? rp(p.harga_modal) + " → " + rp(p.harga_jual)
    : rp(p.harga_modal) + " (modal saja)";

  let badges = "";
  if (p.margin_pct !== null && p.margin_pct !== undefined) {
    const kelas = p.margin_pct >= 0 ? "badge-pos" : "badge-neg";
    const angka = p.margin_pct.toString().replace(".", ",");
    badges += '<span class="badge ' + kelas + '">' + angka + "%</span>";
  }
  if (p.stok_minimum > 0 && p.qty <= p.stok_minimum) {
    badges += '<span class="badge badge-neg">stok menipis</span>';
  }

  return (
    '<a class="card produk-card" href="/ui/barang/' +
    p.id +
    '"><div class="produk-card-atas"><span class="produk-nama">' +
    escapeHtml(p.nama) +
    '</span><span class="produk-qty tabular">' +
    p.qty +
    '</span></div><span class="produk-harga">' +
    hargaJual +
    "</span>" +
    (badges ? '<div class="produk-badges">' + badges + "</div>" : "") +
    "</a>"
  );
}

function kartuKosong() {
  return (
    '<div class="empty-state">' +
    "<p>Belum ada barang</p>" +
    '<a class="btn btn-cta" href="/ui/barang/baru">Tambah barang</a>' +
    "</div>"
  );
}

function render(daftar) {
  const kontainer = document.getElementById("daftar-barang");
  if (daftar.length === 0) {
    kontainer.innerHTML = kartuKosong();
    return;
  }
  kontainer.innerHTML = daftar.map(kartuProduk).join("");
}

document.addEventListener("DOMContentLoaded", async () => {
  const inputCari = document.getElementById("cari-barang");

  try {
    semuaProduk = await api("/api/products");
    semuaProduk.sort((a, b) => a.nama.localeCompare(b.nama, "id"));
  } catch (e) {
    semuaProduk = [];
  }

  if (semuaProduk.length === 0) {
    render([]);
  } else {
    render(semuaProduk);
  }

  inputCari.addEventListener("input", () => {
    const kata = inputCari.value.trim().toLowerCase();
    const hasil = semuaProduk.filter((p) => p.nama.toLowerCase().includes(kata));
    if (semuaProduk.length === 0) {
      render([]);
    } else {
      const kontainer = document.getElementById("daftar-barang");
      kontainer.innerHTML = hasil.length
        ? hasil.map(kartuProduk).join("")
        : '<div class="empty-state"><p>Barang tidak ditemukan</p></div>';
    }
  });
});
