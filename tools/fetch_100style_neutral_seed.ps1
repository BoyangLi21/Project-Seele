param(
    [string]$OutputRoot = "external-assets\incoming\mocap\100style-neutral-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destination = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
if (-not $destination.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output path must remain inside the Project SEELE workspace."
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$sourcePage = "https://www.ianxmason.com/100style/"
$licensePath = Join-Path $destination "100STYLE_OFFICIAL_PAGE.html"
Invoke-WebRequest -UseBasicParsing -Uri $sourcePage -OutFile $licensePath

$files = @(
    @{ File = "Neutral_BR.bvh"; Role = "neutral_backward_run"; Id = "1eCSLTiE0jAjVxM2A8Ln15iM3rieSkp1v" },
    @{ File = "Neutral_BW.bvh"; Role = "neutral_backward_walk"; Id = "1pmJ3GAceoi04kCmXsHvC56TJzKDEHh02" },
    @{ File = "Neutral_FR.bvh"; Role = "neutral_forward_run"; Id = "1vkA3jzorKZ-8UsLGFxKur8imqhyFfnXR" },
    @{ File = "Neutral_FW.bvh"; Role = "neutral_forward_walk"; Id = "1-TqZdIJvpr-QVvAmYJREUZkuAgpAQSfd" },
    @{ File = "Neutral_ID.bvh"; Role = "neutral_idle"; Id = "1Vnz5wnFmOztNzaSBHjSt9v6y0pl0FK8X" },
    @{ File = "Neutral_SR.bvh"; Role = "neutral_side_run"; Id = "1emz3b6EVwKskWyG4Fv8eDHPWRGv3Trbn" },
    @{ File = "Neutral_SW.bvh"; Role = "neutral_side_walk"; Id = "1HzUccloKCjQgpObQ0ZXTEDW7-RllNwHX" },
    @{ File = "Neutral_TR1.bvh"; Role = "neutral_transitions"; Id = "1AnK7HGtuQR4aSVkyWKnZObgapd41KE1N" },
    @{ File = "Dataset_List.csv"; Role = "dataset_catalog"; Id = "19b1zCGOI1ouVhx__GFU5OF0Q2_DN5mnS" },
    @{ File = "Frame_Cuts.csv"; Role = "official_frame_cuts"; Id = "1d0VM8k4UjA4dDmaviuZMjAf-WQNLUwnZ" }
)

$assets = New-Object System.Collections.Generic.List[object]
foreach ($item in $files) {
    $url = "https://drive.google.com/uc?id=$($item.Id)&export=download"
    $path = Join-Path $destination $item.File
    if (-not (Test-Path -LiteralPath $path)) {
        & curl.exe --fail --location --silent --show-error --output $path $url
        if ($LASTEXITCODE -ne 0) {
            throw "100STYLE download failed: $($item.File)"
        }
    }
    if ($item.File.EndsWith(".bvh")) {
        $header = Get-Content -LiteralPath $path -TotalCount 1
        if ($header -ne "HIERARCHY") {
            throw "Invalid BVH header: $($item.File)"
        }
    }
    $assets.Add([ordered]@{
        role = $item.Role
        file = $item.File
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
    license_evidence_file = "100STYLE_OFFICIAL_PAGE.html"
    nominal_frame_rate_hz = 60
    skeleton_bones = 28
    status = "primary_locomotion_candidate_external_3d_only"
    assets = $assets
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $destination "manifest.json") -Encoding utf8
Write-Host "100STYLE Neutral seed downloaded: $($assets.Count) files"
