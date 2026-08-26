param(
    [string]$OutputRoot = "external-assets\incoming\mocap\eva-original-combat-seed-r01"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$destination = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
if (-not $destination.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output path must remain inside the Project SEELE workspace."
}
$cmuDir = Join-Path $destination "cmu_bvh"
New-Item -ItemType Directory -Path $cmuDir -Force | Out-Null

$cmuBase = "https://mocap.cs.cmu.edu"
$mirrorBase = "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data"
$licensePath = Join-Path $destination "CMU_FAQ_LICENSE.html"
Invoke-WebRequest -UseBasicParsing -Uri "$cmuBase/faqs.php" -OutFile $licensePath

$catalogs = @(
    @{ Name = "CMU_SUBJECT_018.html"; Url = "$cmuBase/search.php?subjectnumber=18" },
    @{ Name = "CMU_SUBJECT_019.html"; Url = "$cmuBase/search.php?subjectnumber=19" },
    @{ Name = "CMU_SUBJECT_020.html"; Url = "$cmuBase/search.php?subjectnumber=20" },
    @{ Name = "CMU_SUBJECT_021.html"; Url = "$cmuBase/search.php?subjectnumber=21" },
    @{ Name = "CMU_SUBJECT_022.html"; Url = "$cmuBase/search.php?subjectnumber=22" },
    @{ Name = "CMU_SUBJECT_023.html"; Url = "$cmuBase/search.php?subjectnumber=23" },
    @{ Name = "CMU_SUBJECT_049.html"; Url = "$cmuBase/search.php?subjectnumber=49" },
    @{ Name = "CMU_SUBJECT_090.html"; Url = "$cmuBase/search.php?subjectnumber=90" },
    @{ Name = "CMU_SUBJECT_127.html"; Url = "$cmuBase/search.php?subjectnumber=127" },
    @{ Name = "CMU_SUBJECT_135.html"; Url = "$cmuBase/search.php?subjectnumber=135" },
    @{ Name = "CMU_SUBJECT_141.html"; Url = "$cmuBase/search.php?subjectnumber=141" },
    @{ Name = "CMU_SUBJECT_144.html"; Url = "$cmuBase/search.php?subjectnumber=144" }
)
foreach ($catalog in $catalogs) {
    Invoke-WebRequest -UseBasicParsing -Uri $catalog.Url -OutFile (Join-Path $destination $catalog.Name)
}

$clips = @(
    @{ Subject = 18; Trial = "03"; Role = "paired_pull_actor_a"; Description = "A pulls B; B resists, subject A" },
    @{ Subject = 18; Trial = "04"; Role = "paired_pull_actor_a_alt"; Description = "A pulls B; B resists, subject A alternate" },
    @{ Subject = 18; Trial = "05"; Role = "paired_elbow_pull_actor_a"; Description = "A pulls B by elbow; B resists, subject A" },
    @{ Subject = 18; Trial = "06"; Role = "paired_elbow_pull_actor_a_alt"; Description = "A pulls B by elbow; B resists, subject A alternate" },
    @{ Subject = 19; Trial = "03"; Role = "paired_pull_actor_b"; Description = "A pulls B; B resists, subject B" },
    @{ Subject = 19; Trial = "04"; Role = "paired_pull_actor_b_alt"; Description = "A pulls B; B resists, subject B alternate" },
    @{ Subject = 19; Trial = "05"; Role = "paired_elbow_pull_actor_b"; Description = "A pulls B by elbow; B resists, subject B" },
    @{ Subject = 19; Trial = "06"; Role = "paired_elbow_pull_actor_b_alt"; Description = "A pulls B by elbow; B resists, subject B alternate" },
    @{ Subject = 20; Trial = "10"; Role = "paired_whip_actor_a"; Description = "360-degree two-person whip, subject A" },
    @{ Subject = 21; Trial = "10"; Role = "paired_whip_actor_b"; Description = "360-degree two-person whip, subject B" },
    @{ Subject = 22; Trial = "01"; Role = "paired_pull_up_actor_a"; Description = "B sits; A pulls up B, subject A" },
    @{ Subject = 23; Trial = "01"; Role = "paired_pull_up_actor_b"; Description = "B sits; A pulls up B, subject B" },
    @{ Subject = 22; Trial = "02"; Role = "paired_pull_up_reverse_actor_a"; Description = "A sits; B pulls up A, subject A" },
    @{ Subject = 23; Trial = "02"; Role = "paired_pull_up_reverse_actor_b"; Description = "A sits; B pulls up A, subject B" },
    @{ Subject = 22; Trial = "05"; Role = "paired_two_shoulder_contact_actor_a"; Description = "A places both hands on B shoulders, subject A" },
    @{ Subject = 23; Trial = "05"; Role = "paired_two_shoulder_contact_actor_b"; Description = "A places both hands on B shoulders, subject B" },
    @{ Subject = 22; Trial = "10"; Role = "paired_shelter_actor_a"; Description = "A shelters B from harm, subject A" },
    @{ Subject = 23; Trial = "10"; Role = "paired_shelter_actor_b"; Description = "A shelters B from harm, subject B" },
    @{ Subject = 22; Trial = "11"; Role = "paired_shelter_reverse_actor_a"; Description = "B shelters A from harm, subject A" },
    @{ Subject = 23; Trial = "11"; Role = "paired_shelter_reverse_actor_b"; Description = "B shelters A from harm, subject B" },
    @{ Subject = 22; Trial = "12"; Role = "paired_stumble_collision_actor_a"; Description = "A stumbles into B, subject A" },
    @{ Subject = 23; Trial = "12"; Role = "paired_stumble_collision_actor_b"; Description = "A stumbles into B, subject B" },
    @{ Subject = 22; Trial = "17"; Role = "paired_arm_wrestle_actor_a"; Description = "rush up and arm wrestle, subject A" },
    @{ Subject = 23; Trial = "17"; Role = "paired_arm_wrestle_actor_b"; Description = "rush up and arm wrestle, subject B" },
    @{ Subject = 49; Trial = "04"; Role = "run_leap_a"; Description = "run, leap" },
    @{ Subject = 49; Trial = "05"; Role = "run_leap_b"; Description = "run, leap alternate" },
    @{ Subject = 90; Trial = "05"; Role = "jump_kick_a"; Description = "jump kick" },
    @{ Subject = 90; Trial = "06"; Role = "jump_kick_b"; Description = "jump kick alternate" },
    @{ Subject = 90; Trial = "07"; Role = "jump_kick_c"; Description = "jump kick alternate" },
    @{ Subject = 127; Trial = "23"; Role = "run_dive_roll_a"; Description = "run, dive over, roll, run" },
    @{ Subject = 127; Trial = "24"; Role = "run_dive_roll_b"; Description = "run, dive over, roll, run alternate" },
    @{ Subject = 135; Trial = "04"; Role = "front_kick"; Description = "front kick" },
    @{ Subject = 135; Trial = "07"; Role = "roundhouse_kick"; Description = "mawashigeri roundhouse kick" },
    @{ Subject = 141; Trial = "14"; Role = "punch_kick_sequence"; Description = "punch and kick sequence; reference only" },
    @{ Subject = 144; Trial = "05"; Role = "front_kick_a"; Description = "front kicking" },
    @{ Subject = 144; Trial = "06"; Role = "front_kick_b"; Description = "front kicking alternate" },
    @{ Subject = 144; Trial = "07"; Role = "left_block_a"; Description = "left blocks" },
    @{ Subject = 144; Trial = "08"; Role = "left_block_b"; Description = "left blocks alternate" },
    @{ Subject = 144; Trial = "09"; Role = "left_front_kick_a"; Description = "left front kicking" },
    @{ Subject = 144; Trial = "10"; Role = "left_front_kick_b"; Description = "left front kicking alternate" },
    @{ Subject = 144; Trial = "11"; Role = "left_lunge_a"; Description = "left lunges" },
    @{ Subject = 144; Trial = "12"; Role = "left_lunge_b"; Description = "left lunges alternate" },
    @{ Subject = 144; Trial = "15"; Role = "left_spin_reach_a"; Description = "left spin reach" },
    @{ Subject = 144; Trial = "16"; Role = "left_spin_reach_b"; Description = "left spin reach alternate" },
    @{ Subject = 144; Trial = "17"; Role = "lunge_a"; Description = "lunges" },
    @{ Subject = 144; Trial = "18"; Role = "lunge_b"; Description = "lunges alternate" },
    @{ Subject = 144; Trial = "22"; Role = "reach_left_a"; Description = "reach left" },
    @{ Subject = 144; Trial = "23"; Role = "reach_left_b"; Description = "reach left alternate" },
    @{ Subject = 144; Trial = "24"; Role = "reach_right_a"; Description = "reach right" },
    @{ Subject = 144; Trial = "25"; Role = "reach_right_b"; Description = "reach right alternate" },
    @{ Subject = 144; Trial = "26"; Role = "right_block_a"; Description = "right blocks" },
    @{ Subject = 144; Trial = "27"; Role = "right_block_b"; Description = "right blocks alternate" },
    @{ Subject = 144; Trial = "28"; Role = "right_spin_reach_a"; Description = "right spin reach" },
    @{ Subject = 144; Trial = "29"; Role = "right_spin_reach_b"; Description = "right spin reach alternate" }
)

$assets = New-Object System.Collections.Generic.List[object]
foreach ($clip in $clips) {
    $subject = ([int]$clip.Subject).ToString("000")
    $fileName = "$($clip.Subject.ToString().PadLeft(2, '0'))_$($clip.Trial).bvh"
    $url = "$mirrorBase/$subject/$fileName"
    $filePath = Join-Path $cmuDir $fileName
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $filePath
    $assets.Add([ordered]@{
        role = $clip.Role
        subject = [int]$clip.Subject
        trial = $clip.Trial
        description = $clip.Description
        official_catalog_url = "$cmuBase/search.php?subjectnumber=$($clip.Subject)"
        conversion_mirror_url = $url
        file = "cmu_bvh/$fileName"
        bytes = (Get-Item -LiteralPath $filePath).Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $filePath).Hash.ToLowerInvariant()
        status = "source_candidate_not_runtime_approved"
    })
}

$manifest = [ordered]@{
    schema = 1
    retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
    purpose = "Project SEELE original-aligned combat vocabulary source screening"
    source = "CMU Graphics Lab Motion Capture Database"
    source_url = "$cmuBase/"
    license_evidence_url = "$cmuBase/faqs.php"
    license_evidence_file = "CMU_FAQ_LICENSE.html"
    license_summary = "Official CMU terms permit copying, modification, redistribution and inclusion in products; direct resale of the data is prohibited."
    bvh_conversion = "Bruce Hahn CMU BVH conversion mirrored by una-dinosauria"
    conversion_mirror = "https://github.com/una-dinosauria/cmu-mocap"
    nominal_frame_rate_hz = 120
    source_policy = "biomechanics/contact source only; no clip is accepted without original-skeleton and EVA mesh review"
    assets = $assets
}
$manifestPath = Join-Path $destination "manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Host "EVA original-combat source seed downloaded: $destination"
Write-Host "Clips: $($assets.Count)"
