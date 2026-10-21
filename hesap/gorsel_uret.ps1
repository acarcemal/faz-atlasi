# Paylaşım ve README görsellerini üretir (Türkçe + İngilizce), adres çubuğu olmadan, 2x çözünürlükte.
# Önce yerel sunucu açık olmalı:  python -m http.server 8731 --directory web
# Çalıştırma:  powershell -ExecutionPolicy Bypass -File hesap\gorsel_uret.ps1
$ErrorActionPreference = 'Stop'
$kok = Split-Path -Parent $PSScriptRoot
$web = Join-Path $kok 'web'
$hedef = Join-Path $kok 'gorseller'
$chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") |
  Where-Object { Test-Path $_ } | Select-Object -First 1

# geçici senaryo sayfası: index.html + senaryo scripti
$html = Get-Content (Join-Path $web 'index.html') -Raw -Encoding UTF8
$senaryo = Get-Content (Join-Path $PSScriptRoot 'gorsel_senaryo.js') -Raw -Encoding UTF8
$gecici = Join-Path $web '_gorsel.html'
[IO.File]::WriteAllText($gecici, $html.Replace('</body>', "<script>`n$senaryo`n</script>`n</body>"), [Text.UTF8Encoding]::new($false))

New-Item -ItemType Directory -Force $hedef | Out-Null
$prof = Join-Path $env:TEMP 'fec_gorsel_prof'
$isler = @(
  @{ ad = '1-kesit-42CrMo4'; s = 'kesit'; w = 1600; h = 960 },
  @{ ad = '2-fe-c-diyagrami'; s = 'ikili'; w = 1600; h = 960 },
  @{ ad = '3-bilgi-penceresi'; s = 'bilgi'; w = 1600; h = 960 },
  @{ ad = '4-telefon'; s = 'mobil'; w = 500; h = 1000 }
)
try {
  foreach ($dil in @('tr', 'en')) {
    foreach ($i in $isler) {
      $cikti = Join-Path $hedef ("{0}{1}.png" -f $i.ad, $(if ($dil -eq 'en') { '-en' } else { '' }))
      $arg = @('--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars', "--user-data-dir=`"$prof`"",
        "--window-size=$($i.w),$($i.h)", '--force-device-scale-factor=2', '--virtual-time-budget=6000',
        "--screenshot=`"$cikti`"", "`"http://localhost:8731/_gorsel.html?lang=$dil#$($i.s)`"")
      Start-Process -FilePath $chrome -ArgumentList $arg -NoNewWindow -Wait -RedirectStandardError "$env:TEMP\fec_err.txt"
      "{0}: {1:N0} KB" -f (Split-Path $cikti -Leaf), ((Get-Item $cikti).Length / 1KB)
    }
  }
} finally {
  Remove-Item $gecici, "$env:TEMP\fec_err.txt" -Force -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force $prof -ErrorAction SilentlyContinue
}
