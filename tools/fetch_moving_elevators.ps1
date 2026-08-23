$ErrorActionPreference = "Stop"

function Get-SeeleSha1([string]$Path) {
    $stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).Path)
    $hasher = [System.Security.Cryptography.SHA1]::Create()
    try {
        return ([System.BitConverter]::ToString($hasher.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

$root = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $root ".Codex\local-mods"
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$files = @(
    @{
        Name = "movingelevators-1.4.12-forge-mc1.20.1.jar"
        Url = "https://cdn.modrinth.com/data/9KZOe6HD/versions/noPT9kd8/movingelevators-1.4.12-forge-mc1.20.1.jar"
        Sha1 = "1f61ea052a37e6fe1e927f84c017523155ebd69c"
    },
    @{
        Name = "supermartijn642configlib-1.1.8-forge-mc1.20.jar"
        Url = "https://cdn.modrinth.com/data/LN9BxssP/versions/ZKor79dR/supermartijn642configlib-1.1.8-forge-mc1.20.jar"
        Sha1 = "f80f9eed728966adcfbcc848633e789645057281"
    },
    @{
        Name = "supermartijn642corelib-1.1.24-forge-mc1.20.1.jar"
        Url = "https://cdn.modrinth.com/data/rOUBggPv/versions/1qHDxHxo/supermartijn642corelib-1.1.24-forge-mc1.20.1.jar"
        Sha1 = "866b07e2eb5addbc4a191b7b5ea6aae492ca9905"
    }
)

foreach ($file in $files) {
    $path = Join-Path $destination $file.Name
    if (-not (Test-Path $path)) {
        Invoke-WebRequest -UseBasicParsing -Uri $file.Url -OutFile $path
    }
    $actual = Get-SeeleSha1 $path
    if ($actual -ne $file.Sha1) {
        Remove-Item -Force $path
        throw "Moving Elevators dependency hash mismatch: $($file.Name)"
    }
}
