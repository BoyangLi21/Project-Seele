param(
    [string]$OutputRoot = "external-assets\incoming\mocap\cmu-eva-seed-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destination = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
if (-not $destination.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output path must remain inside the Project SEELE workspace."
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null

$base = "https://mocap.cs.cmu.edu"
$licenseUrl = "$base/faqs.php"
$licensePath = Join-Path $destination "CMU_FAQ_LICENSE.html"
Invoke-WebRequest -UseBasicParsing -Uri $licenseUrl -OutFile $licensePath

$clips = @(
    @{ Subject = 16; Trial = "08"; Role = "run_sudden_stop"; Description = "run/jog, sudden stop" },
    @{ Subject = 16; Trial = "17"; Role = "walk_turn_left_90"; Description = "walk, 90-degree left turn" },
    @{ Subject = 16; Trial = "19"; Role = "walk_turn_right_90"; Description = "walk, 90-degree right turn" },
    @{ Subject = 127; Trial = "04"; Role = "walk_to_run"; Description = "walk to run" },
    @{ Subject = 127; Trial = "05"; Role = "run_quick_stop"; Description = "run to quick stop" },
    @{ Subject = 127; Trial = "13"; Role = "run_sidestep_left"; Description = "run side step left" },
    @{ Subject = 127; Trial = "14"; Role = "run_sidestep_right"; Description = "run side step right" },
    @{ Subject = 127; Trial = "15"; Role = "run_turn_left"; Description = "run turn left" },
    @{ Subject = 127; Trial = "16"; Role = "run_turn_right"; Description = "run turn right" },
    @{ Subject = 127; Trial = "21"; Role = "run_jump_stop_run"; Description = "run jump stop run" },
    @{ Subject = 140; Trial = "01"; Role = "get_up_face_down"; Description = "get up face down" },
    @{ Subject = 140; Trial = "08"; Role = "get_up_on_back"; Description = "get up from ground laying on back" }
)

$subjects = $clips.Subject | Sort-Object -Unique
$assets = New-Object System.Collections.Generic.List[object]
foreach ($subject in $subjects) {
    $subjectText = $subject.ToString()
    $asfName = "$subjectText.asf"
    $asfPath = Join-Path $destination $asfName
    $asfUrl = "$base/subjects/$subject/$subjectText.asf"
    Invoke-WebRequest -UseBasicParsing -Uri $asfUrl -OutFile $asfPath
    $assets.Add([ordered]@{
        role = "skeleton"
        subject = $subject
        trial = $null
        description = "CMU subject skeleton"
        url = $asfUrl
        file = $asfName
        bytes = (Get-Item -LiteralPath $asfPath).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $asfPath).Hash.ToLowerInvariant()
    })
}

foreach ($clip in $clips) {
    $subjectText = ([int]$clip.Subject).ToString()
    $fileName = "${subjectText}_$($clip.Trial).amc"
    $filePath = Join-Path $destination $fileName
    $url = "$base/subjects/$($clip.Subject)/$fileName"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $filePath
    $assets.Add([ordered]@{
        role = $clip.Role
        subject = $clip.Subject
        trial = $clip.Trial
        description = $clip.Description
        url = $url
        file = $fileName
        bytes = (Get-Item -LiteralPath $filePath).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $filePath).Hash.ToLowerInvariant()
    })
}

$manifest = [ordered]@{
    schema = 1
    retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
    source = "CMU Graphics Lab Motion Capture Database"
    source_url = "$base/"
    catalog_url = "$base/subjects.php"
    license_evidence_url = $licenseUrl
    license_evidence_file = "CMU_FAQ_LICENSE.html"
    license_summary = "Official FAQ permits copying, modification, and redistribution without permission."
    format = "ASF/AMC"
    nominal_frame_rate_hz = 120
    status = "provisional_seed_for_external_3d_review"
    assets = $assets
}
$manifestPath = Join-Path $destination "manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "CMU EVA motion seed downloaded: $destination"
Write-Host "Assets: $($assets.Count)"
