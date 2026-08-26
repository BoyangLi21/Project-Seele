param(
    [string]$OutputRoot = "external-assets\incoming\mocap\100style-eva-allowlist-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destination = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
if (-not $destination.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output path must remain inside the Project SEELE workspace."
}

$rawDirectory = Join-Path $destination "third_party_raw"
$evidenceDirectory = Join-Path $destination "provenance"
New-Item -ItemType Directory -Path $rawDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null

$sourcePage = "https://www.ianxmason.com/100style/"
$sourceSnapshot = Join-Path $evidenceDirectory "100STYLE_OFFICIAL_PAGE.html"
Invoke-WebRequest -UseBasicParsing -Uri $sourcePage -OutFile $sourceSnapshot
$html = Get-Content -LiteralPath $sourceSnapshot -Raw

$families = [ordered]@{
    Neutral = @("ID", "FW", "FR", "BW", "BR", "SW", "SR", "TR1")
    StartStop = @("ID", "FW", "FR", "BW", "BR", "SW", "SR", "TR1")
    SpinClock = @("ID", "TR1", "TR2", "TR3")
    SpinAntiClock = @("ID", "TR1", "TR2", "TR3")
    Rushed = @("ID", "FW", "FR", "SW", "SR", "TR1")
    BentForward = @("ID", "FW", "FR", "SW", "SR", "TR1")
    BentKnees = @("ID", "FW", "FR", "SW", "SR", "TR1")
    OnToesBentForward = @("ID", "FW", "FR", "SW", "SR", "TR1")
    OnToesCrouched = @("ID", "FW", "FR", "SW", "SR", "TR1")
    ShieldedLeft = @("ID", "FW", "FR")
    ShieldedRight = @("ID", "FW", "FR")
    TwoFootJump = @("ID", "FW", "FR", "TR1")
}

$desired = New-Object System.Collections.Generic.List[string]
foreach ($family in $families.Keys) {
    foreach ($suffix in $families[$family]) {
        $desired.Add("${family}_${suffix}.bvh")
    }
}
$desired.Add("Dataset_List.csv")
$desired.Add("Frame_Cuts.csv")

$linkMap = @{}
$matches = [regex]::Matches(
    $html,
    '<a\s+href="([^"]+)"[^>]*>([^<]+\.(?:bvh|csv))</a>',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)
foreach ($match in $matches) {
    $url = [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
    $name = [System.Net.WebUtility]::HtmlDecode($match.Groups[2].Value)
    $linkMap[$name] = $url
}

$missing = @($desired | Where-Object { -not $linkMap.ContainsKey($_) })
if ($missing.Count -gt 0) {
    throw "100STYLE official page is missing allowlisted files: $($missing -join ', ')"
}

$assets = New-Object System.Collections.Generic.List[object]
foreach ($name in $desired) {
    $path = Join-Path $rawDirectory $name
    $url = $linkMap[$name]
    if (-not (Test-Path -LiteralPath $path)) {
        & curl.exe --fail --location --silent --show-error --output $path $url
        if ($LASTEXITCODE -ne 0) {
            throw "100STYLE download failed: $name"
        }
    }
    if ($name.EndsWith(".bvh")) {
        $header = Get-Content -LiteralPath $path -TotalCount 1
        if ($header -ne "HIERARCHY") {
            throw "Invalid BVH header: $name"
        }
    }
    $familyName = if ($name.Contains("_")) { $name.Substring(0, $name.IndexOf("_")) } else { "metadata" }
    $assets.Add([ordered]@{
        family = $familyName
        file = "third_party_raw/$name"
        official_download_url = $url
        bytes = (Get-Item -LiteralPath $path).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    })
}

$manifest = [ordered]@{
    schema = 1
    retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
    source = "100STYLE Dataset"
    creator = "Ian Mason, Sebastian Starke, and Taku Komura"
    official_page = $sourcePage
    zenodo_record = "https://zenodo.org/records/8127870"
    license = "CC BY 4.0"
    license_url = "https://creativecommons.org/licenses/by/4.0/"
    license_evidence_file = "provenance/100STYLE_OFFICIAL_PAGE.html"
    nominal_frame_rate_hz = 60
    skeleton_bones = 28
    allowlist_version = "eva_motion_database_audit_r01"
    explicit_deny_families = @("Robot", "DuckFoot", "PigeonToed", "Penguin")
    status = "provisional_external_3d_allowlist_not_runtime"
    assets = $assets
}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $destination "manifest.json") -Encoding utf8

Write-Host "100STYLE EVA allowlist downloaded: $destination"
Write-Host "Assets: $($assets.Count)"
