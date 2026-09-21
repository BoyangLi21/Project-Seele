$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$shader = @(Get-Content -Raw -LiteralPath 'city-shaders.json' | ConvertFrom-Json) | Where-Object { $_.project -eq 'complementary-unbound' }
if (@($shader).Count -ne 1) { throw 'Expected exactly one pinned shader' }
New-Item -ItemType Directory -Force -Path 'shaderpacks','config' | Out-Null
$target = Join-Path (Join-Path $PSScriptRoot 'shaderpacks') $shader.filename
if (-not (Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target -Algorithm SHA512).Hash -ne $shader.sha512) {
    $partial = $target + '.download'
    Invoke-WebRequest -Uri $shader.url -OutFile $partial -UseBasicParsing -UserAgent 'Mozilla/5.0 Project-SEELE/29'
    if ((Get-FileHash -LiteralPath $partial -Algorithm SHA512).Hash -ne $shader.sha512) { throw 'Shader checksum mismatch' }
    Move-Item -LiteralPath $partial -Destination $target -Force
}
$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'config/oculus.properties'), "enableShaders=true`nshaderPack=$($shader.filename)`n", $utf8)
[IO.File]::WriteAllText(($target + '.txt'), "SHADOW_QUALITY=1`nshadowDistance=128.0`nWATER_REFLECT_QUALITY=2`nBLOCK_REFLECT_QUALITY=1`nLIGHTSHAFT_QUALI_DEFINE=1`nSSAO_QUALI_DEFINE=2`nFXAA_DEFINE=1`nDETAIL_QUALITY=2`nCLOUD_QUALITY=2`nCOLORED_LIGHTING=0`nENTITY_SHADOWS_DEFINE=-1`nCAVE_FOG=false`nAMBIENT_MULT=110`nBLOOM_STRENGTH=0.081`n", $utf8)
Write-Host 'Complementary Unbound r5.3 installed from its author source. Disable it in Video Settings > Shader Packs if required.'
