$ErrorActionPreference = 'Stop'
try {
    $targetPath = Join-Path $PSScriptRoot 'SamsungIPBrightness.exe'
    $launchArguments = ''
    if (-not (Test-Path -LiteralPath $targetPath)) {
        $scriptPath = Join-Path $PSScriptRoot 'samsung_brightness.py'
        if (-not (Test-Path -LiteralPath $scriptPath)) { throw 'Application executable or source is missing.' }
        $pythonOutput = & py -3 -c 'import sys, tkinter; assert sys.version_info >= (3,10); print(sys.executable)'
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10+ with Tcl/Tk and the Python launcher.' }
        $targetPath = Join-Path (Split-Path ($pythonOutput | Select-Object -Last 1)) 'pythonw.exe'
        if (-not (Test-Path -LiteralPath $targetPath)) { throw 'pythonw.exe was not found.' }
        $launchArguments = '"' + $scriptPath + '"'
    }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'))) {
        $link = $shell.CreateShortcut((Join-Path $folder 'Samsung IP Brightness.lnk'))
        $link.TargetPath = $targetPath
        $link.Arguments = $launchArguments
        $link.WorkingDirectory = $PSScriptRoot
        $link.Save()
    }
    $answer = Read-Host 'Start automatically at Windows sign-in? [y/N]'
    if ($answer -match '^(y|yes|j|ja)$') {
        $link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'Samsung IP Brightness.lnk'))
        $link.TargetPath = $targetPath
        $link.Arguments = ($launchArguments + ' --background').Trim()
        $link.WorkingDirectory = $PSScriptRoot
        $link.Save()
    }
    if ($launchArguments) {
        Start-Process -FilePath $targetPath -ArgumentList $launchArguments -WorkingDirectory $PSScriptRoot
    } else {
        Start-Process -FilePath $targetPath -WorkingDirectory $PSScriptRoot
    }
    Write-Host 'Shortcuts created. Keep this project folder in place.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
