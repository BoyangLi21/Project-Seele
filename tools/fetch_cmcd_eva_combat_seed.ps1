param(
    [string]$OutputDir = "external-assets/incoming/mocap/cmcd-eva-combat-seed-r01"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = (Resolve-Path ".").Path
$destination = Join-Path $root $OutputDir
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$baseUrl = "https://mocap.web.th-koeln.de"
$files = @(
    @{ File = "Take2018-01-17_12.21.11SAM.bvh"; Role = "paired_fight_actor_safari"; Use = "paired contact/reaction screening only" },
    @{ File = "Take2018-01-17_12.21.11AM.bvh"; Role = "paired_fight_actor_dschungel"; Use = "paired contact/reaction screening only" },
    @{ File = "Take_2019-01-09_E_Kampf.bvh"; Role = "paired_fight_actor_eunuche"; Use = "paired contact/reaction screening only" },
    @{ File = "Take_2019-01-09_N_Kampf.bvh"; Role = "paired_fight_actor_nussknacker"; Use = "paired contact/reaction screening only" },
    @{ File = "Take_2015-11-25_03.05.43_PM_kick.bvh"; Role = "jumping_kick"; Use = "Israfel trajectory/reference screening" },
    @{ File = "Take_2016-01-05_03.43.20_PM.bvh"; Role = "forward_roll_walkover"; Use = "pounce miss/recovery screening" },
    @{ File = "Take_2015-11-25_03.02.43_PM_getsShot.bvh"; Role = "hit_tumble_fall"; Use = "target reaction/recovery screening" },
    @{ File = "Take2018-01-16_KingKong2.bvh"; Role = "ape_defend_fight"; Use = "berserk negative/reference screening only" },
    @{ File = "Take2017-01-11_02.36.38PM.bvh"; Role = "martial_kicking_sequence"; Use = "low-line kick/reap source screening" },
    @{ File = "Take_2019-01-08_karate.bvh"; Role = "karate_sequence"; Use = "low-line kick/reap source screening" },
    @{ File = "Take_2019-01-09_N_Nussknacker1.bvh"; Role = "aggressive_kick_sequence_1"; Use = "low-line kick/reap source screening" },
    @{ File = "Take_2019-01-09_N_Nussknacker3.bvh"; Role = "aggressive_kick_sequence_3"; Use = "low-line kick/reap source screening" }
)

$entries = @()
foreach ($entry in $files) {
    $url = "$baseUrl/mocap_data/$($entry.File)"
    $target = Join-Path $destination $entry.File
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target -TimeoutSec 90
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
    $item = Get-Item -LiteralPath $target
    $entries += [ordered]@{
        file = $entry.File
        role = $entry.Role
        intended_use = $entry.Use
        url = $url
        bytes = $item.Length
        sha256 = $hash
    }
}

$licenseTarget = Join-Path $destination "CMCD_ABOUT_LICENSE.html"
Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/about.php" -OutFile $licenseTarget -TimeoutSec 90
$licenseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $licenseTarget).Hash.ToLowerInvariant()

$manifest = [ordered]@{
    schema = 1
    source = "Cologne Motion Capture Database, TH Koeln"
    source_url = "$baseUrl/index.php"
    license = "CC BY 4.0"
    license_url = "https://creativecommons.org/licenses/by/4.0/"
    license_evidence_url = "$baseUrl/about.php"
    license_evidence_sha256 = $licenseHash
    retrieved_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "downloaded_private_source_candidates_not_runtime_assets"
    entries = $entries
}

$manifestPath = Join-Path $destination "manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output ($manifest | ConvertTo-Json -Depth 8)
