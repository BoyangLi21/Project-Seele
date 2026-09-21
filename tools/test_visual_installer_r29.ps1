$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$testRoot = Join-Path $root ('.Codex/visual-installer-r29-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'deployment_r29/Install-Visuals.ps1') -Destination $testRoot
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'city_shaders_r29.json') -Destination (Join-Path $testRoot 'city-shaders.json')
function Invoke-WebRequest { throw 'Unexpected network access in local-cache test' }
$script = Join-Path $testRoot 'Install-Visuals.ps1'
$game = Join-Path $testRoot 'isolated game with spaces'
& $script -GameDirectory $game -CacheDirectory @((Join-Path $root '.Codex/local-mods'), (Join-Path $root 'run/shaderpacks'))
$config = Join-Path $game 'config/oculus.properties'
Add-Content -LiteralPath $config -Value 'colorSpace=SRGB' -Encoding UTF8
$settings = Join-Path $game 'shaderpacks/ComplementaryUnbound_r5.3.zip.txt'
Add-Content -LiteralPath $settings -Value 'USER_SETTING=keep' -Encoding UTF8
# Second pass must need no cache and no downloads, and preserve user settings.
& $script -GameDirectory $game
$lines = Get-Content -LiteralPath $config -Encoding UTF8
if (@($lines | Where-Object { $_ -eq 'enableShaders=true' }).Count -ne 1) { throw 'Enable option duplicate or missing' }
if ($lines -notcontains 'colorSpace=SRGB') { throw 'Existing option was lost' }
if ((Get-Content -LiteralPath $settings -Encoding UTF8) -notcontains 'USER_SETTING=keep') { throw 'Custom shader options were overwritten' }
$specPath = Join-Path $testRoot 'city-shaders.json'
$entries = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $specPath -Raw -Encoding UTF8)
$bad = @($entries) + @($entries[1])
[IO.File]::WriteAllText($specPath, (ConvertTo-Json -InputObject $bad -Depth 8), [Text.UTF8Encoding]::new($false))
$rejected = $false
try { & $script -GameDirectory (Join-Path $testRoot 'invalid game') } catch { $rejected = $_.Exception.Message -like '*must contain one*' }
if (-not $rejected) { throw 'Ambiguous shader manifest was accepted' }
if (Test-Path -LiteralPath (Join-Path $testRoot 'invalid game')) { throw 'Invalid manifest wrote game files' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'deployment_r29/Setup.ps1') -Destination $game
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'realistic_pack_r25.json') -Destination (Join-Path $game 'realistic-pack.json')
$options = Join-Path $game 'options.txt'
[IO.File]::WriteAllText($options, "resourcePacks:[`"vanilla`",`"mod_resources`",`"file/keep.zip`",`"file/eva_real_model`"]`nincompatibleResourcePacks:[]`n", [Text.UTF8Encoding]::new($false))
& (Join-Path $game 'Setup.ps1') -Kind Client -CacheDirectory @((Join-Path $root 'run/resourcepacks'))
& (Join-Path $game 'Setup.ps1') -Kind Client
$packLine = Get-Content -LiteralPath $options -Encoding UTF8 | Where-Object { $_.StartsWith('resourcePacks:') }
$packs = ConvertFrom-Json -InputObject $packLine.Substring(14)
if (($packs -join '|') -ne 'vanilla|mod_resources|file/keep.zip|file/rotrblocks-v87-128x-2d.zip|file/eva_real_model') { throw 'Texture pack order or existing selection lost' }
Write-Host "PASS: Windows PowerShell $($PSVersionTable.PSVersion), JSON array enumeration, offline cache, repeated installation, settings preservation, duplicate rejection."
