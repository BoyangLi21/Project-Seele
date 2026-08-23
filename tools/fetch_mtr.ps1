$ErrorActionPreference = "Stop"

function Get-SeeleSha256([string]$Path) {
    $stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).Path)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($hasher.ComputeHash($stream))).Replace("-", "")
    }
    finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

$Root = Split-Path -Parent $PSScriptRoot
$TargetDir = Join-Path $Root ".Codex\local-mods"
$Target = Join-Path $TargetDir "MTR-forge-4.0.5+1.20.1.jar"
$ExpectedSha256 = "97466EB715AB02F50A7F7E23F920BF9FDD9D5E4BBB12620C06C6751324C66E9A"
$Url = "https://mediafilez.forgecdn.net/files/8244/920/MTR-forge-4.0.5%2B1.20.1.jar"

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

if (Test-Path -LiteralPath $Target) {
    $Current = Get-SeeleSha256 $Target
    if ($Current -eq $ExpectedSha256) {
        Write-Host "MTR 4.0.5 for Forge 1.20.1 is current."
        exit 0
    }
}

$Temporary = "$Target.download"
Invoke-WebRequest -Uri $Url -OutFile $Temporary -TimeoutSec 180
$Downloaded = Get-SeeleSha256 $Temporary
if ($Downloaded -ne $ExpectedSha256) {
    Remove-Item -LiteralPath $Temporary -Force
    throw "MTR download SHA-256 mismatch: $Downloaded"
}
Move-Item -LiteralPath $Temporary -Destination $Target -Force
Write-Host "Installed MTR 4.0.5 for Forge 1.20.1."
