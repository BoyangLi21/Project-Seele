param()

$ErrorActionPreference = 'Stop'
$TargetDir = Join-Path $PSScriptRoot '..\.Codex\local-mods'
function Get-Sha512($Path) {
    $algorithm = [System.Security.Cryptography.SHA512]::Create()
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $bytes = $algorithm.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

function Install-PinnedMod($FileName, $Url, $Sha512) {
    $Target = Join-Path $TargetDir $FileName
    if (Test-Path -LiteralPath $Target) {
        $Current = Get-Sha512 $Target
        if ($Current -eq $Sha512) {
            Write-Host "$FileName is current."
            return
        }
    }

    $Temporary = "$Target.download"
    Remove-Item -LiteralPath $Temporary -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Temporary
    $Downloaded = Get-Sha512 $Temporary
    if ($Downloaded -ne $Sha512) {
        Remove-Item -LiteralPath $Temporary -Force -ErrorAction SilentlyContinue
        throw "$FileName SHA-512 verification failed."
    }
    Move-Item -LiteralPath $Temporary -Destination $Target -Force
    Write-Host "Installed $FileName"
}

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

$Manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot "r07_vehicle_mods.json") -Raw | ConvertFrom-Json
foreach ($Entry in $Manifest) {
    Install-PinnedMod $Entry.filename $Entry.url $Entry.sha512
}
