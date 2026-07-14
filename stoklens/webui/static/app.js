/* Helper JS bersama untuk semua halaman UI mobile StokLens. */

let toastTimer = null;

/**
 * Tampilkan pesan singkat di #toast, hilang otomatis setelah 4 detik.
 * @param {string} msg
 * @param {boolean} ok - true = normal, false = error (merah)
 */
function toast(msg, ok = true) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", !ok);
  el.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 4000);
}

/**
 * Format angka jadi rupiah gaya "Rp12.345".
 * @param {number} n
 * @returns {string}
 */
function rp(n) {
  return "Rp" + new Intl.NumberFormat("id-ID").format(n);
}

/**
 * Escape karakter HTML supaya aman disisipkan lewat innerHTML.
 * @param {string} s
 * @returns {string}
 */
function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

/**
 * Panggil JSON API. Kalau respons gagal, tampilkan toast error lalu lempar.
 * @param {string} path
 * @param {RequestInit} [opts]
 * @returns {Promise<any>}
 */
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (e) {
      /* respons bukan JSON, pakai statusText */
    }
    toast(detail, false);
    throw new Error(detail);
  }
  return res.json();
}
