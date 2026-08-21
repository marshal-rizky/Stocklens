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
 * Kecilkan foto sebelum diunggah.
 *
 * Kamera HP menghasilkan 12-24MP (±3-7 MB per foto), padahal YOLO menyusutkannya
 * ke 640px dan CLIP ke 224px — resolusi penuh dibuang di sisi server. Mengecilkan
 * di sini memangkas unggahan jadi ±300 KB: penting saat opname dilakukan di toko
 * lewat kuota HP, dan mencegah request timeout untuk scan banyak foto.
 *
 * imageOrientation "from-image" WAJIB: foto potret menyimpan piksel landscape plus
 * flag EXIF, dan canvas tidak memutarnya sendiri. Tanpa ini foto terkirim miring
 * 90 derajat dan deteksi anjlok.
 *
 * @param {File} file
 * @param {number} [maks] - sisi terpanjang hasil, piksel
 * @returns {Promise<File>} file baru, atau file asli kalau sudah kecil/gagal proses
 */
async function kecilkanFoto(file, maks = 1280) {
  if (!file.type.startsWith("image/")) return file;
  let bitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch (e) {
    return file; /* format tak terbaca browser (mis. HEIC) — biar server yang urus */
  }
  const skala = Math.min(1, maks / Math.max(bitmap.width, bitmap.height));
  if (skala === 1) {
    bitmap.close();
    return file;
  }
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * skala);
  canvas.height = Math.round(bitmap.height * skala);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();

  const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.9));
  if (!blob) return file;
  return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg",
                  { type: "image/jpeg" });
}

/**
 * Kecilkan sekumpulan foto sekaligus.
 * @param {File[]} files
 * @returns {Promise<File[]>}
 */
function kecilkanSemua(files) {
  return Promise.all(files.map((f) => kecilkanFoto(f)));
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
  const { silent, ...fetchOpts } = opts || {};
  let res;
  try {
    res = await fetch(path, fetchOpts);
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
