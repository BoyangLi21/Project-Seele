param(
    [string]$SeedRoot = "external-assets\incoming\mocap\cmu-eva-seed-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$sourceRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $SeedRoot))
if (-not $sourceRoot.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Seed path must remain inside the Project SEELE workspace."
}
$manifestPath = Join-Path $sourceRoot "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "CMU seed manifest is missing."
}

$toolRoot = Join-Path $projectRoot "external-assets\incoming\tools\amc2bvh-v0.1.0"
$archive = Join-Path $toolRoot "amc2bvh-0.1.0_x86_64_windows.zip"
$tool = Join-Path $toolRoot "bin\amc2bvh-0.1.0_x86_64_windows\amc2bvh.exe"
$toolUrl = "https://github.com/thcopeland/amc2bvh/releases/download/v0.1.0/amc2bvh-0.1.0_x86_64_windows.zip"
$toolSha256 = "8320c23da9954470df92a022fe044103de3a65ac5b232fe546d8328e1fb59366"
if (-not (Test-Path -LiteralPath $tool)) {
    New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri $toolUrl -OutFile $archive
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
    if ($actual -ne $toolSha256) {
        throw "amc2bvh archive hash mismatch."
    }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $toolRoot "bin")
}
if (-not (Test-Path -LiteralPath $archive)) {
    throw "amc2bvh archive is missing; reproducible hash cannot be checked."
}
$actualToolArchiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant()
if ($actualToolArchiveHash -ne $toolSha256) {
    throw "amc2bvh archive hash mismatch."
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$outputRoot = Join-Path $sourceRoot "bvh"
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$converted = New-Object System.Collections.Generic.List[object]
foreach ($asset in $manifest.assets) {
    if ($asset.role -eq "skeleton") {
        continue
    }
    $asf = Join-Path $sourceRoot "$($asset.subject).asf"
    $amc = Join-Path $sourceRoot $asset.file
    $bvhName = [System.IO.Path]::ChangeExtension($asset.file, ".bvh")
    $bvh = Join-Path $outputRoot $bvhName
    & $tool $asf $amc -f 120 -c 8 -o $bvh
    if ($LASTEXITCODE -ne 0) {
        throw "amc2bvh failed for $($asset.file)."
    }
    $head = Get-Content -LiteralPath $bvh -TotalCount 3
    if ($head[0] -ne "HIERARCHY" -or $head[1] -notmatch '^ROOT root$') {
        throw "Invalid BVH header for $bvhName."
    }
    $frameLine = Select-String -LiteralPath $bvh -Pattern '^Frames:\s+(\d+)$' | Select-Object -First 1
    if ($null -eq $frameLine) {
        throw "BVH frame count missing for $bvhName."
    }
    $converted.Add([ordered]@{
        role = $asset.role
        subject = $asset.subject
        trial = $asset.trial
        source_amc = $asset.file
        output_bvh = "bvh/$bvhName"
        frames = [int]$frameLine.Matches[0].Groups[1].Value
        bytes = (Get-Item -LiteralPath $bvh).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $bvh).Hash.ToLowerInvariant()
    })
}

$report = [ordered]@{
    schema = 1
    converted_at_utc = [DateTime]::UtcNow.ToString("o")
    converter = "thcopeland/amc2bvh v0.1.0"
    converter_repository = "https://github.com/thcopeland/amc2bvh"
    converter_license = "MIT"
    converter_archive_url = $toolUrl
    converter_archive_sha256 = $toolSha256
    source_manifest = "manifest.json"
    frame_rate_hz = 120
    status = "converted_not_retargeted_not_accepted"
    assets = $converted
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $sourceRoot "bvh_manifest.json") -Encoding utf8
Write-Host "CMU seed converted to BVH: $($converted.Count) clips"
