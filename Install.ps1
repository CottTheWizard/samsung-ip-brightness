$ErrorActionPreference = 'Stop'
try {
    $scriptPath = Join-Path $PSScriptRoot 'samsung_brightness.py'
    if (-not (Test-Path -LiteralPath $scriptPath)) { throw 'Application source is missing.' }
    $pythonOutput = & py -3 -c 'import sys, tkinter; assert sys.version_info >= (3,10); print(sys.executable)'
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10+ with Tcl/Tk and the Python launcher.' }
    $pythonWindowed = Join-Path (Split-Path ($pythonOutput | Select-Object -Last 1)) 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonWindowed)) { throw 'pythonw.exe was not found.' }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))) {
        $link = $shell.CreateShortcut((Join-Path $folder 'Samsung IP Brightness.lnk'))
        $link.TargetPath = $pythonWindowed
        $link.Arguments = '"' + $scriptPath + '"'
        $link.WorkingDirectory = $PSScriptRoot
        $link.Save()
    }
    $answer = Read-Host 'Start automatically at Windows sign-in? [y/N]'
    if ($answer -match '^(y|yes|j|ja)$') {
        $link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'Samsung IP Brightness.lnk'))
        $link.TargetPath = $pythonWindowed
        $link.Arguments = '"' + $scriptPath + '" --background'
        $link.WorkingDirectory = $PSScriptRoot
        $link.Save()
    }
    Start-Process -FilePath $pythonWindowed -ArgumentList ('"' + $scriptPath + '"') -WorkingDirectory $PSScriptRoot
    Write-Host 'Shortcuts created. Keep this project folder in place.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
