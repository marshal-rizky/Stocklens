# Jalankan StokLens untuk DIREKAM dari HP lewat WiFi yang sama.
#
# Bedanya dengan jalan_hybrid.ps1: tidak memakai tunnel sama sekali. Uvicorn
# di-bind ke 0.0.0.0 supaya bisa dibuka dari HP lewat alamat IP lokal.
#
# Kenapa penting untuk video: narasi menyebut foto tidak dikirim ke layanan
# pihak ketiga. Kalau address bar menampilkan trycloudflare.com, itu
# kontradiksi yang gratis untuk ditunjuk juri. Alamat IP privat di address bar
# justru membuktikan sebaliknya secara kasat mata.
#
#   powershell -ExecutionPolicy Bypass -File scripts\jalan_rekam.ps1
#
# Guard: kalau STOKLENS_PASSWORD di-set, browser HP akan meminta login dulu.
# Untuk rekaman yang bersih, jalankan tanpa env itu (jaringan lokal saja).

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$port = 8000

# Ambil IP LAN yang sesungguhnya. Adapter virtual (VirtualBox, WSL, Hyper-V)
# punya alamat 192.168.56.x atau serupa yang TIDAK bisa dijangkau HP.
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object { $_.IPAddress -notlike "127.*" -and
                      $_.IPAddress -notlike "169.254.*" -and
                      $_.InterfaceAlias -notmatch "VirtualBox|VMware|WSL|Hyper-V|Loopback" } |
       Sort-Object -Property SkipAsSource, InterfaceIndex |
       Select-Object -First 1).IPAddress
if (-not $ip) { throw "Tidak menemukan alamat IP lokal. Pastikan terhubung ke WiFi atau kabel." }

# Firewall: tanpa aturan ini Windows memblokir koneksi dari HP dan gejalanya
# cuma "tidak bisa dibuka", tanpa petunjuk apa pun.
$adaAturan = Get-NetFirewallRule -DisplayName "StokLens 8000" -ErrorAction SilentlyContinue
if (-not $adaAturan) {
    try {
        New-NetFirewallRule -DisplayName "StokLens 8000" -Direction Inbound `
            -LocalPort $port -Protocol TCP -Action Allow -Profile Private | Out-Null
        Write-Host "Aturan firewall dibuat (profil Private)." -ForegroundColor Green
    } catch {
        Write-Host "GAGAL membuat aturan firewall. Jalankan PowerShell sebagai" -ForegroundColor Red
        Write-Host "Administrator sekali saja, atau izinkan lewat dialog Windows" -ForegroundColor Red
        Write-Host "yang muncul saat uvicorn start." -ForegroundColor Red
    }
}

if ($env:STOKLENS_PASSWORD) {
    Write-Host "CATATAN: STOKLENS_PASSWORD aktif, HP akan diminta login dulu." -ForegroundColor Yellow
    Write-Host "Untuk rekaman bersih, tutup jendela ini dan jalankan di shell baru." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Buka dari HP (WiFi yang sama):" -ForegroundColor Cyan
Write-Host "     http://${ip}:${port}" -ForegroundColor White
Write-Host ""
Write-Host "  Ctrl+C untuk berhenti." -ForegroundColor DarkGray
Write-Host ""

# --timeout-keep-alive 120: bawaan uvicorn 5 detik terlalu pendek untuk
# pemakaian dari HP. Pengguna membaca laporan selama puluhan detik, lalu menekan
# tombol tepat ketika server menutup koneksi yang menganggur, dan browser
# melaporkannya sebagai "tidak bisa terhubung ke server" walau servernya sehat.
python -m uvicorn stoklens.api:create_app --factory --host 0.0.0.0 --port $port --timeout-keep-alive 120
