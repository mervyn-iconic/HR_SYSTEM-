param([string]$InstallPath = 'D:\HR_SYSTEM--Main\hrms')
$ErrorActionPreference = 'Stop'
try {
    if (!(Test-Path (Join-Path $InstallPath 'app.py'))) {
        throw "Cannot find the HR installation at $InstallPath."
    }
    $port = 5000
    if ($env:PORT) { $port = [int]$env:PORT }
    $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) {
        throw "Stop the running HR app with Ctrl+C in its server window, then run this updater again. Port $port is still in use."
    }
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Select the original Golden Marketing logo image'
    $picker.Filter = 'Company logo (*.png;*.jpg;*.jpeg;*.webp)|*.png;*.jpg;*.jpeg;*.webp'
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-Host 'Update cancelled. No installation files were changed.'
        exit 0
    }
    $logo = $picker.FileName
    $extension = [System.IO.Path]::GetExtension($logo).ToLowerInvariant()
    $staging = Join-Path $env:TEMP ('GoldenMarketing-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $staging | Out-Null
    # Stage the chosen original before replacing any existing files.
    $stagedLogo = Join-Path $staging ('company-logo' + $extension)
    Copy-Item -LiteralPath $logo -Destination $stagedLogo
    Write-Host 'Downloading the latest Golden Marketing HR system...'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/mervyn-iconic/HR_SYSTEM-/archive/refs/heads/Main.zip' -OutFile (Join-Path $staging 'update.zip')
    Expand-Archive -LiteralPath (Join-Path $staging 'update.zip') -DestinationPath (Join-Path $staging 'source')
    $launcher = Get-ChildItem (Join-Path $staging 'source') -Filter start_windows.bat -Recurse | Select-Object -First 1
    if (!$launcher) { throw 'Downloaded archive does not contain the application. Your installation was not changed.' }
    $source = $launcher.Directory.FullName
    foreach ($required in @('app.py','templates\index.html','static\app.js','static\style.css')) {
        if (!(Test-Path (Join-Path $source $required))) { throw "Incomplete update: $required is missing." }
    }
    $backup = Join-Path (Split-Path $InstallPath -Parent) ('hrms-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,6))
    New-Item -ItemType Directory -Path $backup | Out-Null
    # Include existing records and code while excluding disposable Python environments.
    Get-ChildItem -LiteralPath $InstallPath -Force |
        Where-Object { $_.Name -notin @('.venv','.venv-hr','__pycache__') } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $backup -Recurse -Force }
    Write-Host "Backup saved to: $backup"
    Get-ChildItem -LiteralPath $source -Force |
        Where-Object { $_.Name -notin @('hrms.db','.env','.venv','.venv-hr') } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $InstallPath -Recurse -Force }
    # Remove alternate logo formats so the newly selected original always wins.
    foreach ($ext in @('.png','.jpg','.jpeg','.webp')) {
        $old = Join-Path $InstallPath ('static\company-logo' + $ext)
        if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old }
    }
    Copy-Item -LiteralPath $stagedLogo -Destination (Join-Path $InstallPath ('static\company-logo' + $extension))
    Write-Host 'Update complete. Your original logo is installed throughout the system.' -ForegroundColor Green
    Start-Process -FilePath (Join-Path $InstallPath 'start_windows.bat') -WorkingDirectory $InstallPath
    Write-Host "When the app starts, open http://127.0.0.1:$port and press Ctrl+Shift+R."
} catch {
    Write-Error "Update stopped: $($_.Exception.Message)"
    exit 1
}
