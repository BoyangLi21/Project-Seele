# gen_sounds.ps1 - Project SEELE original synthesized sound generator.
# Usage:  powershell -File tools/gen_sounds.ps1 [-OutDir <dir>]
# Needs:  ffmpeg on PATH (wav -> ogg vorbis)
# Rule:   every waveform is pure math (sine/saw/noise); no sampled material,
#         no melodies imitating the source work. Keep this file ASCII-only:
#         PowerShell 5.1 misparses BOM-less UTF-8 comments.
param(
    [string]$OutDir = "$PSScriptRoot\..\src\main\resources\assets\projectseele\sounds"
)

$ErrorActionPreference = 'Stop'
$SampleRate = 44100

function Write-Wav {
    param([string]$Path, [float[]]$Samples)
    # Normalize to 0.82 peak to avoid clipping.
    $peak = 0.0001
    foreach ($s in $Samples) { $a = [Math]::Abs($s); if ($a -gt $peak) { $peak = $a } }
    $gain = 0.82 / $peak
    $dataLen = $Samples.Count * 2
    $fs = [System.IO.File]::Create($Path)
    $bw = New-Object System.IO.BinaryWriter($fs)
    $bw.Write([byte[]][char[]]'RIFF'); $bw.Write([int](36 + $dataLen)); $bw.Write([byte[]][char[]]'WAVE')
    $bw.Write([byte[]][char[]]'fmt '); $bw.Write([int]16); $bw.Write([int16]1); $bw.Write([int16]1)
    $bw.Write([int]$SampleRate); $bw.Write([int]($SampleRate * 2)); $bw.Write([int16]2); $bw.Write([int16]16)
    $bw.Write([byte[]][char[]]'data'); $bw.Write([int]$dataLen)
    foreach ($s in $Samples) {
        $v = [Math]::Max(-1.0, [Math]::Min(1.0, $s * $gain))
        $bw.Write([int16]([Math]::Round($v * 32767)))
    }
    $bw.Close(); $fs.Close()
}

function New-Buf { param([double]$Seconds) ,(New-Object float[] ([int]($Seconds * $SampleRate))) }

function Saw { param([double]$Phase) 2.0 * ($Phase - [Math]::Floor($Phase + 0.5)) }

$rng = New-Object System.Random(20260706)  # fixed seed: reproducible output

# ---------- 1. alarm: two-tone air-raid siren, seamless 1.8s loop ----------
Write-Host "synth: alarm"
$buf = New-Buf 1.8
$n = $buf.Count
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $seg = [Math]::Floor($t / 0.45) % 2          # switch tone every 0.45s
    $f = if ($seg -eq 0) { 660.0 } else { 524.0 }
    $vib = 1.0 + 0.006 * [Math]::Sin(2 * [Math]::PI * 5.2 * $t)
    $ph = $f * $vib * $t
    # fundamental + odd harmonics -> horn-like timbre
    $v = [Math]::Sin(2 * [Math]::PI * $ph) + 0.34 * [Math]::Sin(2 * [Math]::PI * 3 * $ph) + 0.15 * [Math]::Sin(2 * [Math]::PI * 5 * $ph)
    # 15ms fades at segment edges kill clicks and make the loop seamless
    $segT = $t % 0.45
    $env = [Math]::Min(1.0, [Math]::Min($segT / 0.015, (0.45 - $segT) / 0.015))
    $buf[$i] = [float]($v * $env * 0.9)
}
Write-Wav "$env:TEMP\seele_alarm.wav" $buf

# ---------- 2. beam_charge: 2.6s rising energy sweep ----------
Write-Host "synth: beam_charge"
$buf = New-Buf 2.6
$n = $buf.Count
$ph = 0.0
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $prog = $t / 2.6
    $f = 170.0 * [Math]::Pow(8.2, $prog)          # 170Hz -> ~1400Hz exponential sweep
    $ph += $f / $SampleRate
    $trem = 1.0 - (0.42 * (1 - $prog)) * (0.5 + 0.5 * [Math]::Sin(2 * [Math]::PI * (5 + 9 * $prog) * $t))
    $v = 0.62 * [Math]::Sin(2 * [Math]::PI * $ph) + 0.30 * (Saw $ph) + 0.16 * [Math]::Sin(2 * [Math]::PI * 2.01 * $ph)
    $env = [Math]::Min(1.0, $t / 0.25) * (0.55 + 0.45 * $prog)
    $buf[$i] = [float]($v * $trem * $env)
}
Write-Wav "$env:TEMP\seele_beam_charge.wav" $buf

# ---------- 3. beam_fire: 1.5s positron discharge ----------
Write-Host "synth: beam_fire"
$buf = New-Buf 1.5
$n = $buf.Count
$ph = 0.0; $lp = 0.0
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $f = 240.0 * [Math]::Pow(0.38, $t)            # falling pitch
    $ph += $f / $SampleRate
    $crack = 0.0
    if ($t -lt 0.05) { $crack = ($rng.NextDouble() * 2 - 1) * (1 - $t / 0.05) }   # initial arc noise
    $noise = ($rng.NextDouble() * 2 - 1)
    $lp = $lp + 0.06 * ($noise - $lp)              # low-passed hiss
    $body = 0.55 * (Saw $ph) + 0.35 * [Math]::Sin(2 * [Math]::PI * $ph) + 0.45 * [Math]::Sin(2 * [Math]::PI * 55 * $t)
    $env = [Math]::Exp(-2.1 * $t)
    $buf[$i] = [float](($body * $env) + ($lp * 0.8 * $env) + $crack * 0.9)
}
Write-Wav "$env:TEMP\seele_beam_fire.wav" $buf

# ---------- 4. cross_explosion: 2.6s cross blast ----------
Write-Host "synth: cross_explosion"
$buf = New-Buf 2.6
$n = $buf.Count
$lp = 0.0
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $noise = ($rng.NextDouble() * 2 - 1)
    $cut = 0.5 * [Math]::Exp(-1.9 * $t) + 0.012    # low-pass narrows over time
    $lp = $lp + $cut * ($noise - $lp)
    $boom = [Math]::Sin(2 * [Math]::PI * (46 * $t - 14 * $t * $t)) * [Math]::Exp(-1.6 * $t)
    $ring = 0.20 * [Math]::Sin(2 * [Math]::PI * 890 * $t) * [Math]::Exp(-3.2 * $t)
    $env = [Math]::Min(1.0, $t / 0.012) * [Math]::Exp(-1.15 * $t)
    $buf[$i] = [float](($lp * 1.15 + $boom * 0.95 + $ring) * $env)
}
Write-Wav "$env:TEMP\seele_cross_explosion.wav" $buf

# ---------- 5. crystal_hit: 0.32s glassy impact ----------
Write-Host "synth: crystal_hit"
$buf = New-Buf 0.32
$n = $buf.Count
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $v = 0.5 * [Math]::Sin(2 * [Math]::PI * 2140 * $t) + 0.34 * [Math]::Sin(2 * [Math]::PI * 3170 * $t) + 0.22 * [Math]::Sin(2 * [Math]::PI * 4690 * $t)
    $tick = 0.0
    if ($t -lt 0.008) { $tick = ($rng.NextDouble() * 2 - 1) * (1 - $t / 0.008) * 0.6 }
    $buf[$i] = [float]($v * [Math]::Exp(-16.0 * $t) + $tick)
}
Write-Wav "$env:TEMP\seele_crystal_hit.wav" $buf

# ---------- 6. crystal_break: 1.3s descending shatter ----------
Write-Host "synth: crystal_break"
$buf = New-Buf 1.3
$n = $buf.Count
$pings = @(2680.0, 2140.0, 1690.0, 1340.0, 1060.0, 842.0)
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $v = 0.0
    for ($p = 0; $p -lt $pings.Count; $p++) {
        $start = 0.05 * $p
        if ($t -ge $start) {
            $dt = $t - $start
            $v += (0.5 - 0.05 * $p) * [Math]::Sin(2 * [Math]::PI * $pings[$p] * $dt) * [Math]::Exp(-9.0 * $dt)
        }
    }
    $shatter = ($rng.NextDouble() * 2 - 1) * [Math]::Exp(-5.5 * $t) * 0.5
    $buf[$i] = [float]($v + $shatter)
}
Write-Wav "$env:TEMP\seele_crystal_break.wav" $buf

# ---------- 7. drill: 1.0s grind, seamless loop ----------
Write-Host "synth: drill"
$buf = New-Buf 1.0
$n = $buf.Count
$lp = 0.0
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $noise = ($rng.NextDouble() * 2 - 1)
    $lp = $lp + 0.18 * ($noise - $lp)
    $buzz = (Saw (88.0 * $t)) * 0.55 + (Saw (66.2 * $t)) * 0.35
    $flutter = 0.72 + 0.28 * [Math]::Sin(2 * [Math]::PI * 13.0 * $t)
    # 20ms edge fades -> seamless when retriggered
    $env = [Math]::Min(1.0, [Math]::Min($t / 0.02, (1.0 - $t) / 0.02))
    $buf[$i] = [float](($buzz + $lp * 0.9) * $flutter * $env)
}
Write-Wav "$env:TEMP\seele_drill.wav" $buf

# ---------- 8. ramiel_hum: 2.4s ambient drone ----------
Write-Host "synth: ramiel_hum"
$buf = New-Buf 2.4
$n = $buf.Count
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    # 110Hz + 164.6Hz beating -> deep uneasy chord
    $v = 0.5 * [Math]::Sin(2 * [Math]::PI * 110.0 * $t) + 0.42 * [Math]::Sin(2 * [Math]::PI * 164.6 * $t) + 0.18 * [Math]::Sin(2 * [Math]::PI * 220.7 * $t)
    $env = [Math]::Min(1.0, [Math]::Min($t / 0.3, (2.4 - $t) / 0.3))
    $buf[$i] = [float]($v * $env * (0.8 + 0.2 * [Math]::Sin(2 * [Math]::PI * 0.7 * $t)))
}
Write-Wav "$env:TEMP\seele_ramiel_hum.wav" $buf

# ---------- 9. rifle_fire: 0.5s positron rifle zap ----------
Write-Host "synth: rifle_fire"
$buf = New-Buf 0.5
$n = $buf.Count
$ph = 0.0
for ($i = 0; $i -lt $n; $i++) {
    $t = $i / [double]$SampleRate
    $f = 1350.0 * [Math]::Pow(0.16, $t * 2.2)
    $ph += $f / $SampleRate
    $zap = 0.6 * (Saw $ph) + 0.3 * [Math]::Sin(2 * [Math]::PI * $ph * 2.02)
    $click = 0.0
    if ($t -lt 0.012) { $click = ($rng.NextDouble() * 2 - 1) * (1 - $t / 0.012) }
    $buf[$i] = [float]($zap * [Math]::Exp(-9.5 * $t) + $click * 0.8)
}
Write-Wav "$env:TEMP\seele_rifle_fire.wav" $buf

# ---------- WAV -> OGG ----------
New-Item -ItemType Directory -Force $OutDir | Out-Null
$names = @('alarm', 'beam_charge', 'beam_fire', 'cross_explosion', 'crystal_hit', 'crystal_break', 'drill', 'ramiel_hum', 'rifle_fire')
foreach ($name in $names) {
    & ffmpeg -y -loglevel error -i "$env:TEMP\seele_$name.wav" -c:a libvorbis -q:a 4 -ac 1 -ar 44100 "$OutDir\$name.ogg"
    Remove-Item "$env:TEMP\seele_$name.wav" -Force
    Write-Host "ogg: $name.ogg"
}
Write-Host "done -> $OutDir"
