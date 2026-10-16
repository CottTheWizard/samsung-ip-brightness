$ErrorActionPreference = 'Stop'
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'), [Environment]::GetFolderPath('Startup'))) {
    $shortcutPath = Join-Path $folder 'Samsung IP Brightness.lnk'
    if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath }
}
Write-Host 'Shortcuts removed. Quit the app, then delete its source folder if desired.'
Write-Host 'Pairing data is preserved in %LOCALAPPDATA%\SamsungIPBrightness.'
