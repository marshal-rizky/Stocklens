# Jalankan StokLens di PC (GPU) dan ekspos ke internet lewat Cloudflare Tunnel.
#
# Mode hybrid: seluruh aplikasi tetap di PC ini - DB, YOLO, CLIP semuanya lokal,
# inference pakai RTX 4070. Tunnel cuma menyalurkan HTTP dari luar ke sini, jadi
# tim bisa opname dari HP di toko tanpa laptop dan tanpa biaya hosting.
#
# PC harus menyala selama tim memakainya. Tutup jendela ini = URL mati.
#
#   powershell -ExecutionPolicy Bypass -File scripts\jalan_hybrid.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $env:STOKLENS_PASSWORD) {
    Write-Host 'STOKLENS_PASSWORD belum di-set. Tanpa itu app terbuka untuk siapa pun' -ForegroundColor Red
    Write-Host 'yang menemukan URL-nya. Set dulu:  setx STOKLENS_PASSWORD kata-sandi' -ForegroundColor Red
    exit 1
}

# MSI cloudflared menambah PATH, tapi jendela yang sudah terbuka sebelum instalasi
# belum melihatnya. Cari manual supaya skrip tetap jalan tanpa restart terminal.
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
    $cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
    if (-not (Test-Path $cf)) { throw "cloudflared tidak ditemukan. Install: winget install Cloudflare.cloudflared" }
}

$port = 8000
Write-Host "1/2  uvicorn di 127.0.0.1:$port" -ForegroundColor Cyan
# Bind ke 127.0.0.1, bukan 0.0.0.0: satu-satunya jalan masuk adalah tunnel,
# jadi app tidak ikut terbuka ke seluruh WiFi/jaringan lokal.
$app = Start-Process -PassThru -NoNewWindow python `
    -ArgumentList "-m", "uvicorn", "stoklens.api:create_app", "--factory",
                  "--host", "127.0.0.1", "--port", "$port"

try {
    # Tunggu app benar-benar melayani. 401 = sudah hidup dan guard aktif.
    $siap = $false
    foreach ($i in 1..30) {
        Start-Sleep -Seconds 1
        try {
            Invoke-WebRequest "http://127.0.0.1:$port/ui/beranda" -TimeoutSec 2 -UseBasicParsing | Out-Null
            $siap = $true; break
        } catch {
            if ($_.Exception.Response.StatusCode.value__ -eq 401) { $siap = $true; break }
        }
    }
    if (-not $siap) { throw "uvicorn tidak merespons setelah 30 detik" }
    Write-Host "     app hidup, guard aktif" -ForegroundColor Green

    Write-Host "2/2  Cloudflare Tunnel - URL publik muncul di bawah" -ForegroundColor Cyan
    Write-Host '     login: user "stoklens", password = isi STOKLENS_PASSWORD' -ForegroundColor Yellow
    Write-Host "     Ctrl+C untuk menghentikan semuanya.`n" -ForegroundColor DarkGray
    & $cf tunnel --url "http://127.0.0.1:$port"
}
finally {
    if ($app -and -not $app.HasExited) { Stop-Process -Id $app.Id -Force }
    Write-Host "`nuvicorn dihentikan." -ForegroundColor DarkGray
}
