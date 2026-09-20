param([ValidateSet('Server','Client')][string]$Kind, [string]$Java = 'java')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if ($Kind -eq 'Server') {
    if ($Java -eq 'java' -and $env:JAVA_HOME) { $Java = Join-Path $env:JAVA_HOME 'bin\java.exe' }
    $spec = Get-Content -Raw -LiteralPath 'forge-runtime.json' | ConvertFrom-Json
    $url = $spec.url
    $target = Join-Path $PSScriptRoot $spec.filename
    $algorithm = 'SHA1'
    $expected = $spec.sha1
} else {
    $spec = Get-Content -Raw -LiteralPath 'realistic-pack.json' | ConvertFrom-Json
    New-Item -ItemType Directory -Force -Path 'resourcepacks' | Out-Null
    $url = $spec.download_url
    $target = Join-Path (Join-Path $PSScriptRoot 'resourcepacks') $spec.filename
    $algorithm = 'SHA512'
    $expected = $spec.sha512
}
$valid = (Test-Path -LiteralPath $target) -and ((Get-FileHash -LiteralPath $target -Algorithm $algorithm).Hash -eq $expected)
if (-not $valid) {
    $partial = $target + '.download'
    Write-Host "Downloading from the official source: $url"
    Invoke-WebRequest -Uri $url -OutFile $partial -UseBasicParsing -UserAgent 'Mozilla/5.0 Project-SEELE/26'
    if ((Get-FileHash -LiteralPath $partial -Algorithm $algorithm).Hash -ne $expected) { throw 'Download checksum mismatch' }
    Move-Item -LiteralPath $partial -Destination $target -Force
}
if ($Kind -eq 'Server') {
    & $Java -jar $target --installServer
    if ($LASTEXITCODE -ne 0) { throw 'Forge installation failed; Java 17 and network access are required.' }
    Write-Host 'Forge installed. Import the world, review eula.txt, then run Start-Server.bat.'
} else {
    $options = Join-Path $PSScriptRoot 'options.txt'
    $lines = @(Get-Content -LiteralPath $options -Encoding UTF8)
    $key = 'file/' + $spec.filename
    $found = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i].StartsWith('resourcePacks:')) {
            $packs = @($lines[$i].Substring(14) | ConvertFrom-Json)
            $packs = @($packs | Where-Object { $_ -ne $key -and $_ -ne 'file/eva_real_model' })
            $packs += @($key, 'file/eva_real_model')
            $lines[$i] = 'resourcePacks:' + (ConvertTo-Json -InputObject @($packs) -Compress)
            $found = $true
            break
        }
    }
    if (-not $found) { $lines += 'resourcePacks:' + (ConvertTo-Json -InputObject @($key,'file/eva_real_model') -Compress) }
    $found = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i].StartsWith('incompatibleResourcePacks:')) {
            $accepted = @($lines[$i].Substring(26) | ConvertFrom-Json)
            if ($accepted -notcontains $key) { $accepted += $key }
            $lines[$i] = 'incompatibleResourcePacks:' + (ConvertTo-Json -InputObject @($accepted) -Compress)
            $found = $true
            break
        }
    }
    if (-not $found) { $lines += 'incompatibleResourcePacks:' + (ConvertTo-Json -InputObject @($key) -Compress) }
    [IO.File]::WriteAllLines($options, $lines, [Text.UTF8Encoding]::new($false))
    Write-Host '128x textures installed and enabled below the EVA models. Start your Forge 1.20.1 instance.'
}
