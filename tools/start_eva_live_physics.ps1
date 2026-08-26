param(
    [ValidateSet("Start", "Stop", "Status")]
    [string]$Mode = "Start"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runRoot = Join-Path $projectRoot "run"
$logRoot = Join-Path $runRoot "logs"
$pidFile = Join-Path $runRoot "seele_physics_live.pid"
$sharedFile = Join-Path $runRoot "seele_physics_live.bin"
$python = "C:\ProgramData\miniconda3\envs\seele-physics\python.exe"
$script = Join-Path $projectRoot "tools\run_eva_live_physics_sidecar.py"
$checkpoint = Join-Path $projectRoot "results\g1_p1_capture_future_tracker_r63\epoch_10.ckpt"
$motion = Join-Path $projectRoot "artifacts\motion_research\physics_v1\G1_P1_CAPTURE_STEP_D048_CONTACT_REPAIRED_R62.pt"

function Get-SidecarProcess {
    if (-not (Test-Path -LiteralPath $pidFile)) {
        return $null
    }
    $text = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($text -notmatch '^\d+$') {
        return $null
    }
    $processId = [int]$text
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $null
    }
    if ($process.CommandLine -notlike "*run_eva_live_physics_sidecar.py*") {
        throw "PID file does not reference the Project SEELE physics sidecar."
    }
    return $process
}

function Stop-Sidecar {
    $process = Get-SidecarProcess
    if ($null -ne $process) {
        Stop-Process -Id $process.ProcessId -Force
    }
    if (Test-Path -LiteralPath $pidFile) {
        Remove-Item -LiteralPath $pidFile -Force
    }
}

if ($Mode -eq "Stop") {
    Stop-Sidecar
    Write-Host "Project SEELE live physics sidecar stopped."
    exit 0
}

if ($Mode -eq "Status") {
    $process = Get-SidecarProcess
    if ($null -eq $process) {
        Write-Host "Project SEELE live physics sidecar is not running."
        exit 1
    }
    Write-Host "Project SEELE live physics sidecar PID=$($process.ProcessId)."
    exit 0
}

foreach ($required in @($python, $script, $checkpoint, $motion)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required live physics asset is missing: $required"
    }
}

Stop-Sidecar
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stdout = Join-Path $logRoot "eva_live_physics.out.log"
$stderr = Join-Path $logRoot "eva_live_physics.err.log"
$env:MUJOCO_GL = "disable"
$arguments = @(
    $script,
    "--live-shared", $sharedFile,
    "--live-motion-id", "1",
    "--live-auto-impulse-seconds", "2.5",
    "--live-auto-impulse-dv", "-0.5",
    "--checkpoint", $checkpoint,
    "--simulator", "mujoco",
    "--num-envs", "1",
    "--motion-file", $motion,
    "--headless",
    "--full-eval"
)
$process = Start-Process -FilePath $python -ArgumentList $arguments `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr
Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
Write-Host "Project SEELE live physics sidecar starting: PID=$($process.Id)"
Write-Host "First checkpoint materialization can take about one minute."
