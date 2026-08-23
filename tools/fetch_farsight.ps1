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
    Write-Host "Installed client-only $FileName"
}

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
Install-PinnedMod `
    'farsight-1.20.1-5.1.jar' `
    'https://edge.forgecdn.net/files/8192/522/farsight-1.20.1-5.1.jar' `
    '1e37b58c6fd29e915bc9cdddd858a3e583a6b09b9096563b541cdfd90951f17261d937982b1cadf626fe1da4884de27b9e59baed2c67adfe68d580f4f30f85c8'
Install-PinnedMod `
    'cupboard-1.20.1-3.9.jar' `
    'https://edge.forgecdn.net/files/8382/158/cupboard-1.20.1-3.9.jar' `
    'cc781f2099b3431e77556fc9c215d646571b75c1330c478af8f955f59b4af0b06a89cc5b72063d1635fc9c4ca682cb85e59c8930c058106d075d2ab90ddea84a'
