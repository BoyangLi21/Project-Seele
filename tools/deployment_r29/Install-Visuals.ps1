param([string]$GameDirectory = '', [string[]]$CacheDirectory = @())
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not $GameDirectory) {
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'LatestLaunch.bat')) {
        throw 'This is the PCL launcher folder. Import the SEELE AllInOne ZIP into PCL, or pass -GameDirectory with the isolated game folder shown by PCL.'
    }
    $GameDirectory = $PSScriptRoot
}
$GameDirectory = [IO.Path]::GetFullPath($GameDirectory)
$entries = ConvertFrom-Json -InputObject (Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $PSScriptRoot 'city-shaders.json'))
# Windows PowerShell 5.1 can emit a JSON array as one pipeline object.
# Enumerate its entries explicitly before filtering; do not filter that array.
$shaders = @(foreach ($entry in $entries) { if ($entry.project -ceq 'complementary-unbound') { $entry } })
$loaders = @(foreach ($entry in $entries) { if ($entry.project -ceq 'oculus') { $entry } })
if ($shaders.Count -ne 1 -or $loaders.Count -ne 1) { throw 'city-shaders.json must contain one Complementary shader and one Oculus loader.' }
$shader = $shaders[0]
foreach ($entry in @($loaders[0], $shader)) {
    if ([IO.Path]::GetFileName($entry.filename) -cne $entry.filename) { throw 'Invalid artifact filename' }
    $folder = if ($entry.project -eq 'oculus') { 'mods' } else { 'shaderpacks' }
    $directory = Join-Path $GameDirectory $folder
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $target = Join-Path $directory $entry.filename
    $valid = (Test-Path -LiteralPath $target) -and ((Get-FileHash -LiteralPath $target -Algorithm SHA512).Hash -eq $entry.sha512)
    if (-not $valid) {
        foreach ($cache in $CacheDirectory) {
            $cached = Join-Path $cache $entry.filename
            if ((Test-Path -LiteralPath $cached) -and ((Get-FileHash -LiteralPath $cached -Algorithm SHA512).Hash -eq $entry.sha512)) {
                Copy-Item -LiteralPath $cached -Destination $target -Force
                $valid = $true
                Write-Host "Reused verified local file: $($entry.filename)"
                break
            }
        }
    }
    if (-not $valid) {
        $partial = $target + '.download'
        Invoke-WebRequest -Uri $entry.url -OutFile $partial -UseBasicParsing -UserAgent 'Mozilla/5.0 Project-SEELE/29'
        if ((Get-FileHash -LiteralPath $partial -Algorithm SHA512).Hash -ne $entry.sha512) { throw 'Visual artifact checksum mismatch' }
        Move-Item -LiteralPath $partial -Destination $target -Force
    }
}
$utf8 = [Text.UTF8Encoding]::new($false)
$configFolder = Join-Path $GameDirectory 'config'
New-Item -ItemType Directory -Force -Path $configFolder | Out-Null
$config = Join-Path $configFolder 'oculus.properties'
$lines = if (Test-Path -LiteralPath $config) { @(Get-Content -LiteralPath $config -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*(enableShaders|shaderPack)\s*=' }) } else { @() }
$lines = @($lines) + @('enableShaders=true', ('shaderPack=' + $shader.filename))
[IO.File]::WriteAllLines($config, $lines, $utf8)
$settings = Join-Path (Join-Path $GameDirectory 'shaderpacks') ($shader.filename + '.txt')
if (-not (Test-Path -LiteralPath $settings)) {
    [IO.File]::WriteAllText($settings, "SHADOW_QUALITY=1`nshadowDistance=128.0`nWATER_REFLECT_QUALITY=2`nBLOCK_REFLECT_QUALITY=1`nLIGHTSHAFT_QUALI_DEFINE=1`nSSAO_QUALI_DEFINE=2`nFXAA_DEFINE=1`nDETAIL_QUALITY=2`nCLOUD_QUALITY=2`nCOLORED_LIGHTING=0`nENTITY_SHADOWS_DEFINE=-1`nCAVE_FOG=false`nAMBIENT_MULT=110`nBLOOM_STRENGTH=0.081`n", $utf8)
}
Write-Host "Visuals ready in: $GameDirectory"
Write-Host 'Complementary Unbound r5.3 enabled. Existing valid files were reused.'
