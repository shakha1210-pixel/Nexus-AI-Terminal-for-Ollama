[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $Root ".build"
$Venv = Join-Path $BuildRoot "windows-venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$DistRoot = Join-Path $Root "dist\windows"
$InstallerScript = Join-Path $PSScriptRoot "installer.iss"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $File $($Arguments -join ' ')"
    }
}

Push-Location $Root
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python 3.11+ topilmadi. Python o'rnating va PATH ga qo'shing."
    }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Node.js/npm topilmadi. Node.js 20+ o'rnating."
    }

    $PythonVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $VersionParts = $PythonVersion.Split(".")
    if ([int]$VersionParts[0] -lt 3 -or ([int]$VersionParts[0] -eq 3 -and [int]$VersionParts[1] -lt 11)) {
        throw "Python 3.11 yoki yangiroq versiya kerak (topildi: $PythonVersion)."
    }

    if ($Clean) {
        Remove-Item $DistRoot -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $BuildRoot "pyinstaller") -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $BuildRoot "spec") -Recurse -Force -ErrorAction SilentlyContinue
    }

    New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
    if (-not (Test-Path $Python)) {
        Invoke-Native -File "python" -Arguments @("-m", "venv", $Venv)
    }

    Invoke-Native -File $Python -Arguments @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Native -File $Python -Arguments @("-m", "pip", "install", "-r", "backend/requirements.txt", "-r", "desktop/requirements.txt")

    Push-Location frontend
    try {
        Invoke-Native -File "npm" -Arguments @("ci")
        Invoke-Native -File "npm" -Arguments @("run", "build")
    }
    finally {
        Pop-Location
    }

    Invoke-Native -File $Python -Arguments @("scripts/create_icon.py")

    $PyInstallerArgs = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "NEXUS AI",
        "--icon", "$Root\desktop\assets\icon.ico",
        "--paths", "backend",
        "--paths", ".",
        "--distpath", "dist/windows",
        "--workpath", ".build/pyinstaller",
        "--specpath", ".build/spec",
        "--add-data", "$Root\backend\app;backend\app",
        "--add-data", "$Root\frontend\dist;frontend\dist",
        "--add-data", "$Root\desktop\assets;desktop\assets",
        "--collect-all", "webview",
        "--collect-all", "pystray",
        "--collect-all", "keyring",
        "--collect-all", "uvicorn",
        "--collect-all", "certifi",
        "--collect-all", "PIL",
        "--hidden-import", "app.main",
        "--hidden-import", "desktop.tray",
        "--hidden-import", "desktop.ollama_manager",
        "desktop/launcher.py"
    )
    Invoke-Native -File $Python -Arguments $PyInstallerArgs

    # Kaggle's CLI is a separate executable used by the notebook search/download service.
    # Dummy build-only credentials let PyInstaller inspect Kaggle modules without embedding real secrets.
    $PreviousKaggleUsername = $env:KAGGLE_USERNAME
    $PreviousKaggleKey = $env:KAGGLE_KEY
    try {
        $env:KAGGLE_USERNAME = "nexus-build-placeholder"
        $env:KAGGLE_KEY = "nexus-build-placeholder"
        $KaggleArgs = @(
            "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--console",
            "--name", "kaggle",
            "--distpath", "dist/windows/NEXUS AI",
            "--workpath", ".build/kaggle-cli",
            "--specpath", ".build/spec-kaggle",
            "--collect-all", "kaggle",
            "desktop/kaggle_cli.py"
        )
        Invoke-Native -File $Python -Arguments $KaggleArgs
    }
    finally {
        $env:KAGGLE_USERNAME = $PreviousKaggleUsername
        $env:KAGGLE_KEY = $PreviousKaggleKey
    }

    $Executable = Join-Path $DistRoot "NEXUS AI\NEXUS AI.exe"
    if (-not (Test-Path $Executable)) {
        throw "PyInstaller bajarilmadi: $Executable topilmadi."
    }
    if (-not (Test-Path (Join-Path $DistRoot "NEXUS AI\kaggle.exe"))) {
        throw "Kaggle CLI paketi yaratilmadi."
    }

    $Iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        $Candidates = @(
            (Join-Path ([Environment]::GetFolderPath("ProgramFilesX86")) "Inno Setup 6\ISCC.exe"),
            (Join-Path ([Environment]::GetFolderPath("ProgramFiles")) "Inno Setup 6\ISCC.exe")
        ) | Where-Object { $_ -and (Test-Path $_) }
        if ($Candidates.Count -gt 0) {
            $IsccPath = $Candidates[0]
        }
        else {
            throw "Inno Setup 6 topilmadi. Uni o'rnating: https://jrsoftware.org/isinfo.php"
        }
    }
    else {
        $IsccPath = $Iscc.Source
    }

    Invoke-Native -File $IsccPath -Arguments @($InstallerScript)

    $Setup = Join-Path $Root "dist\installer\NEXUS-AI-Setup.exe"
    if (-not (Test-Path $Setup)) {
        throw "Installer yaratilmadi: $Setup topilmadi."
    }
    Write-Host "Windows installer tayyor: $Setup" -ForegroundColor Green
}
finally {
    Pop-Location
}
