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

/**
 * Render daftar produk. Kalau kosong, tampilkan pesanKosong (HTML string).
 * @param {object[]} daftar
 * @param {string} pesanKosong
 */
function render(daftar, pesanKosong) {
  const kontainer = document.getElementById("daftar-barang");
  kontainer.innerHTML = daftar.length
    ? daftar.map(kartuProduk).join("")
    : pesanKosong;
}

const PESAN_BELUM_ADA =
  '<div class="empty-state">' +
  "<p>Belum ada barang</p>" +
  '<a class="btn btn-cta" href="/ui/barang/baru">Tambah barang</a>' +
  "</div>";

const PESAN_TIDAK_KETEMU = '<div class="empty-state"><p>Barang tidak ditemukan</p></div>';

function tampilkanErrorMuat() {
  const kontainer = document.getElementById("daftar-barang");
  kontainer.innerHTML =
    '<div class="card error-state"><p>Gagal memuat</p>' +
    '<button type="button" class="btn" id="coba-lagi">Coba lagi</button></div>';
  document.getElementById("coba-lagi").addEventListener("click", muatBarang);
}

async function muatBarang() {
  try {
    semuaProduk = await api("/api/products");
  } catch (e) {
    /* state ERROR, bukan state kosong: toast sudah tampil dari api() */
    tampilkanErrorMuat();
    return;
  }
  semuaProduk.sort((a, b) => a.nama.localeCompare(b.nama, "id"));
  render(semuaProduk, PESAN_BELUM_ADA);
}

document.addEventListener("DOMContentLoaded", () => {
  muatBarang();

  document.getElementById("cari-barang").addEventListener("input", (ev) => {
    const kata = ev.target.value.trim().toLowerCase();
    const hasil = semuaProduk.filter((p) => p.nama.toLowerCase().includes(kata));
    /* daftar sumber kosong = belum ada barang; hasil filter kosong = tidak ketemu */
    render(hasil, semuaProduk.length ? PESAN_TIDAK_KETEMU : PESAN_BELUM_ADA);
  });
});
