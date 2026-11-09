param(
    [string]$ImageName = "nexus-agent-sandbox:py311"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$dockerfile = Join-Path $repoRoot "backend/sandbox/Dockerfile"
$buildContext = Join-Path $repoRoot "backend/sandbox"
$checks = @()
$containerName = "nexus-agent-smoke-" + [guid]::NewGuid().ToString("N")
$probePath = Join-Path $env:TEMP ("nexus-agent-smoke-" + [guid]::NewGuid().ToString("N") + ".txt")
$expectedContent = "NEXUS_DOCKER_SANDBOX_SMOKE_OK"

function Add-Check([string]$Name, [bool]$Passed, [string]$Details) {
    $script:checks += [pscustomobject]@{
        Check = $Name
        Passed = $Passed
        Details = $Details
    }
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI topilmadi. Docker Desktop'ni o'rnating va qayta urinib ko'ring."
    }

    $serverVersion = & docker info --format '{{.ServerVersion}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker daemon bilan aloqa yo'q. Docker Desktop ishga tushganini tekshiring. $serverVersion"
    }
    Add-Check "Docker daemon" $true "Docker Engine $serverVersion"

    if (-not (Test-Path $dockerfile)) {
        throw "Dockerfile topilmadi: $dockerfile"
    }

    Write-Host "Building sandbox image: $ImageName"
    & docker build --pull -t $ImageName -f $dockerfile $buildContext
    if ($LASTEXITCODE -ne 0) {
        throw "Sandbox image build muvaffaqiyatsiz tugadi."
    }
    Add-Check "Sandbox image build" $true $ImageName

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    if ($probePath.Contains(",")) {
        throw "Temporary file path contains a comma, which Docker --mount cannot safely parse."
    }
    [System.IO.File]::WriteAllText($probePath, $expectedContent, $utf8)

    $probeScript = "import json,pathlib; print(json.dumps({'content':pathlib.Path('/input/file').read_text(encoding='utf-8')}))"
    $runArgs = @(
        "run",
        "--name", $containerName,
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=16",
        "--memory=96m",
        "--memory-swap=96m",
        "--cpus=0.50",
        "--user=65532:65532",
        "--ulimit", "nofile=32:32",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=1m",
        "--mount", "type=bind,source=$probePath,target=/input/file,readonly",
        $ImageName,
        "-c", $probeScript
    )

    Write-Host "Running one-file isolated container..."
    $runOutput = & docker @runArgs 2>&1
    $runExitCode = $LASTEXITCODE
    if ($runExitCode -ne 0) {
        throw "Sandbox container ishga tushmadi (exit $runExitCode): $runOutput"
    }

    $payload = ($runOutput | Out-String).Trim() | ConvertFrom-Json
    Add-Check "Read-only file mount" ($payload.content -ceq $expectedContent) "Container faqat vaqtinchalik probe faylni o'qidi."

    $inspectOutput = & docker inspect $containerName 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Container konfiguratsiyasini docker inspect orqali o'qib bo'lmadi: $inspectOutput"
    }
    $container = @((($inspectOutput | Out-String) | ConvertFrom-Json))[0]
    $hostConfig = $container.HostConfig
    $mount = @($container.Mounts | Where-Object { $_.Destination -eq "/input/file" }) | Select-Object -First 1

    Add-Check "Network isolation" ($hostConfig.NetworkMode -eq "none") "HostConfig.NetworkMode=$($hostConfig.NetworkMode)"
    Add-Check "Read-only root filesystem" ([bool]$hostConfig.ReadonlyRootfs) "ReadonlyRootfs=$($hostConfig.ReadonlyRootfs)"
    Add-Check "All Linux capabilities dropped" (@($hostConfig.CapDrop) -contains "ALL") "CapDrop=$(@($hostConfig.CapDrop) -join ',')"
    Add-Check "No-new-privileges" (@($hostConfig.SecurityOpt | Where-Object { $_ -like "no-new-privileges*" }).Count -gt 0) "SecurityOpt=$(@($hostConfig.SecurityOpt) -join ',')"
    Add-Check "Resource limits" (
        $hostConfig.PidsLimit -eq 16 -and
        $hostConfig.Memory -eq 100663296 -and
        $hostConfig.NanoCpus -eq 500000000
    ) "PIDs=$($hostConfig.PidsLimit), memory=$($hostConfig.Memory), NanoCpus=$($hostConfig.NanoCpus)"
    Add-Check "Non-root container user" ($container.Config.User -eq "65532:65532") "User=$($container.Config.User)"
    Add-Check "Single-file mount is read-only" ($null -ne $mount -and -not [bool]$mount.RW) "Mount RW=$($mount.RW)"
    Add-Check "Container exited successfully" ($container.State.ExitCode -eq 0) "ExitCode=$($container.State.ExitCode)"
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        & docker rm -f $containerName 2>$null | Out-Null
    }
    if (Test-Path $probePath) {
        Remove-Item -LiteralPath $probePath -Force
    }
}

$checks | Format-Table -AutoSize
$failed = @($checks | Where-Object { -not $_.Passed })
if ($failed.Count -gt 0) {
    Write-Host "$($failed.Count) ta smoke-test tekshiruvi muvaffaqiyatsiz." -ForegroundColor Red
    exit 1
}

Write-Host "Docker sandbox smoke-test muvaffaqiyatli yakunlandi." -ForegroundColor Green
Write-Host "Container va vaqtinchalik probe fayl tozalandi; image saqlab qolindi."
