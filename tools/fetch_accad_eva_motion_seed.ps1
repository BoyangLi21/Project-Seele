param(
    [string]$OutputRoot = "external-assets\incoming\mocap\accad-eva-seed-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destination = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
if (-not $destination.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output path must remain inside the Project SEELE workspace."
}

$rawDirectory = Join-Path $destination "third_party_raw"
$expandedDirectory = Join-Path $destination "third_party_normalized\source_extract"
$evidenceDirectory = Join-Path $destination "provenance"
New-Item -ItemType Directory -Path $rawDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $expandedDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null

$sourcePage = "https://accad.osu.edu/research/motion-lab/mocap-system-and-data"
$licenseUrl = "https://creativecommons.org/licenses/by/3.0/"
$sourceSnapshot = Join-Path $evidenceDirectory "ACCAD_OFFICIAL_DATA_PAGE.html"
$licenseSnapshot = Join-Path $evidenceDirectory "CC_BY_3_0_DEED.html"
Invoke-WebRequest -UseBasicParsing -Uri $sourcePage -OutFile $sourceSnapshot
Invoke-WebRequest -UseBasicParsing -Uri $licenseUrl -OutFile $licenseSnapshot

$packages = @(
    @{
        Id = "male2_bvh"
        Role = "combat_and_transition_skeleton_seed"
        Archive = "Male2_bvh.zip"
        Url = "https://accad.osu.edu/sites/accad.osu.edu/files/Male2_bvh.zip"
        Index = "ACCAD_mocap_Data_Male_2.pdf"
        IndexUrl = "https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male_2.pdf"
    },
    @{
        Id = "male2_martial_arts_kicks_c3d"
        Role = "unarmed_kick_reference"
        Archive = "Male2MartialArtsKicks_c3d.zip"
        Url = "https://accad.osu.edu/sites/accad.osu.edu/files/Male2MartialArtsKicks_c3d.zip"
        Index = "ACCAD_mocap_Data_Male2_MartialArtsKicks.pdf"
        IndexUrl = "https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male2_MartialArtsKicks.pdf"
    },
    @{
        Id = "male2_martial_arts_punches_c3d"
        Role = "unarmed_punch_reference"
        Archive = "Male2MartialArtsPunches_c3d.zip"
        Url = "https://accad.osu.edu/sites/accad.osu.edu/files/Male2MartialArtsPunches_c3d.zip"
        Index = "ACCAD_mocap_Data_Male2_MartialArtsPunches.pdf"
        IndexUrl = "https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male2_MartialArtsPunches.pdf"
    },
    @{
        Id = "male2_martial_arts_stances_c3d"
        Role = "combat_stance_and_transition_reference"
        Archive = "Male2MartialArtsStances_c3d.zip"
        Url = "https://accad.osu.edu/sites/accad.osu.edu/files/Male2MartialArtsStances_c3d.zip"
        Index = "ACCAD_mocap_Data_Male2_MartialArtsStances.pdf"
        IndexUrl = "https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male2_MartialArtsStances.pdf"
    },
    @{
        Id = "male2_martial_arts_walks_turns_c3d"
        Role = "combat_footwork_turn_block_dodge_reference"
        Archive = "MartialArtsWalksTurns_c3d.zip"
        Url = "https://accad.osu.edu/sites/accad.osu.edu/files/MartialArtsWalksTurns_c3d.zip"
        Index = "ACCAD_mocap_Data_Male2_MartialArtsWalksTurns.pdf"
        IndexUrl = "https://accad.osu.edu/sites/accad.osu.edu/files/ACCAD_mocap_Data_Male2_MartialArtsWalksTurns.pdf"
    }
)

$assets = New-Object System.Collections.Generic.List[object]
foreach ($package in $packages) {
    $archivePath = Join-Path $rawDirectory $package.Archive
    if (-not (Test-Path -LiteralPath $archivePath)) {
        & curl.exe --fail --location --silent --show-error --output $archivePath $package.Url
        if ($LASTEXITCODE -ne 0) {
            throw "ACCAD download failed: $($package.Archive)"
        }
    }

    $stream = [System.IO.File]::OpenRead($archivePath)
    try {
        $signature = New-Object byte[] 4
        [void]$stream.Read($signature, 0, 4)
    }
    finally {
        $stream.Dispose()
    }
    if ($signature[0] -ne 0x50 -or $signature[1] -ne 0x4B) {
        throw "Invalid ZIP signature: $($package.Archive)"
    }

    $indexPath = Join-Path $evidenceDirectory $package.Index
    Invoke-WebRequest -UseBasicParsing -Uri $package.IndexUrl -OutFile $indexPath

    $packageExtract = Join-Path $expandedDirectory $package.Id
    if (Test-Path -LiteralPath $packageExtract) {
        Remove-Item -LiteralPath $packageExtract -Recurse -Force
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $packageExtract
    $inventory = @(
        Get-ChildItem -LiteralPath $packageExtract -Recurse -File |
            Sort-Object FullName |
            ForEach-Object {
                [ordered]@{
                    file = $_.FullName.Substring($packageExtract.Length).TrimStart("\").Replace("\", "/")
                    bytes = $_.Length
                    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
                }
            }
    )

    $assets.Add([ordered]@{
        id = $package.Id
        role = $package.Role
        official_download_url = $package.Url
        archive = "third_party_raw/$($package.Archive)"
        bytes = (Get-Item -LiteralPath $archivePath).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
        official_index_url = $package.IndexUrl
        official_index_file = "provenance/$($package.Index)"
        extracted_file_count = $inventory.Count
        extracted_files = $inventory
    })
}

$manifest = [ordered]@{
    schema = 1
    retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
    source = "ACCAD Open Motion Project"
    creator = "Advanced Computing Center for the Arts and Design, The Ohio State University"
    official_page = $sourcePage
    license = "CC BY 3.0 Unported"
    license_url = $licenseUrl
    license_evidence_files = @(
        "provenance/ACCAD_OFFICIAL_DATA_PAGE.html",
        "provenance/CC_BY_3_0_DEED.html"
    )
    use_policy = "Public candidate source. Attribution and modification notice required. Clips remain rejected until source-skeleton, contact, retarget, and aesthetic review pass."
    source_frame_rate_hz = "unverified_per_package"
    status = "provisional_external_3d_seed_not_runtime"
    assets = $assets
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $destination "manifest.json") -Encoding utf8

Write-Host "ACCAD EVA motion seed downloaded: $destination"
Write-Host "Packages: $($assets.Count)"
