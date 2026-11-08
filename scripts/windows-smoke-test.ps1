$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$checks = @()

function Add-Check([string]$Name, [bool]$Passed, [string]$Details) {
    $script:checks += [pscustomobject]@{ Check = $Name; Passed = $Passed; Details = $Details }
}

$python = Get-Command python -ErrorAction SilentlyContinue
Add-Check "Python available" ($null -ne $python) $(if ($python) { $python.Source } else { "python not found" })

$frontendBuild = Test-Path (Join-Path $repoRoot "frontend/dist/index.html")
Add-Check "Frontend build" $frontendBuild "Run npm ci and npm run build in frontend/ if missing."

$webviewPath = Join-Path $env:LOCALAPPDATA "Microsoft/EdgeWebView/Application"
$webviewInstalled = Test-Path $webviewPath
if (-not $webviewInstalled) {
    $webviewPath = Join-Path ${env:ProgramFiles(x86)} "Microsoft/EdgeWebView/Application"
    $webviewInstalled = Test-Path $webviewPath
}
Add-Check "WebView2 Runtime files" $webviewInstalled "Install the Evergreen Runtime from https://developer.microsoft.com/microsoft-edge/webview2/ if missing."

$iconPath = Join-Path $repoRoot "desktop/assets/icon.ico"
$iconExists = Test-Path $iconPath
Add-Check "Desktop icon" $iconExists "Run: python scripts/create_icon.py"

$desktopRequirements = Test-Path (Join-Path $repoRoot "desktop/requirements.txt")
Add-Check "Desktop requirements file" $desktopRequirements "desktop/requirements.txt must exist."

$checks | Format-Table -AutoSize
if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
    Write-Host "Some checks need attention. This script does not launch the app or install components." -ForegroundColor Yellow
    exit 1
}
Write-Host "Preflight checks passed. Next run: python desktop/launcher.py" -ForegroundColor Green
