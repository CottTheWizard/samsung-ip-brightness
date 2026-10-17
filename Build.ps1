$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    py -3 -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Build dependencies could not be installed.' }
    py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name SamsungIPBrightness --hidden-import windows_tray --hidden-import daily_schedule samsung_brightness.py
    if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
    $packagePath = Join-Path $PSScriptRoot 'dist\SamsungIPBrightness-windows-x64.zip'
    $files = @('dist\SamsungIPBrightness.exe', 'Install.ps1', 'Uninstall.ps1', 'Start.cmd', 'README.md', 'README.de.md', 'LICENSE')
    Compress-Archive -LiteralPath $files -DestinationPath $packagePath -Force
    $hash = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash.ToLowerInvariant()
    ($hash + '  SamsungIPBrightness-windows-x64.zip') | Set-Content -LiteralPath 'dist\SHA256SUMS.txt' -Encoding ASCII
    Write-Host 'Built dist\SamsungIPBrightness.exe and Windows ZIP package.'
} finally {
    Pop-Location
}
