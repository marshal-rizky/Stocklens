/* Helper JS bersama untuk semua halaman UI mobile StokLens. */

const PESAN_OFFLINE = "Tidak bisa terhubung ke server";

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
 * Parse input angka gaya lokal ("3.500", "Rp 3.500", "-5") jadi integer.
 * Strip semua karakter non-digit (minus di depan dipertahankan).
 * @param {string} str
 * @returns {number} NaN kalau tidak ada digit
 */
function angka(str) {
  const s = String(str).trim();
  const negatif = s.startsWith("-");
  const digits = s.replace(/\D/g, "");
  if (!digits) return NaN;
  return parseInt((negatif ? "-" : "") + digits, 10);
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
 * Panggil JSON API. Kalau respons gagal, tampilkan toast error lalu lempar,
 * kecuali opts.silent true (dipakai caller yang mau tangani sendiri lewat
 * e.status / e.detail, misal untuk bedakan 404/409 dari error lain).
 * @param {string} path
 * @param {RequestInit & {silent?: boolean}} [opts]
 * @returns {Promise<any>}
 */
async function api(path, opts) {
  const silent = !!(opts && opts.silent);
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    /* kegagalan level jaringan (offline, server mati) */
    if (!silent) toast(PESAN_OFFLINE, false);
    throw e;
  }
  if (!res.ok) {
    let detail; // detail dari body server, undefined kalau tidak ada
    let pesanToast = res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail) {
        detail = body.detail;
        pesanToast = body.detail;
      }
    } catch (e) {
      /* respons bukan JSON, pakai statusText */
    }
    if (!silent) toast(pesanToast, false);
    const err = new Error(pesanToast);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return res.json();
}
