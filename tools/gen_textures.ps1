# gen_textures.ps1 - Project SEELE placeholder texture generator (32x32).
# All art is procedural: parts are defined along a 45-degree diagonal axis
# (u = distance along the barrel, v = signed offset across it), which gives
# pixel-perfect diagonals without hand-typing 32 rows of characters.
# Keep this file ASCII-only: PowerShell 5.1 misparses BOM-less UTF-8.
Add-Type -AssemblyName System.Drawing

$root = Join-Path $PSScriptRoot '..\src\main\resources\assets\projectseele\textures'
New-Item -ItemType Directory -Force "$root\item" | Out-Null
New-Item -ItemType Directory -Force "$root\entity" | Out-Null

function New-Canvas([int]$Size) { New-Object System.Drawing.Bitmap($Size, $Size) }

function Set-Px([System.Drawing.Bitmap]$Bmp, [int]$X, [int]$Y, [int[]]$Argb) {
    if ($X -ge 0 -and $X -lt $Bmp.Width -and $Y -ge 0 -and $Y -lt $Bmp.Height) {
        $Bmp.SetPixel($X, $Y, [System.Drawing.Color]::FromArgb($Argb[0], $Argb[1], $Argb[2], $Argb[3]))
    }
}

# Diagonal coordinates for a 32x32 canvas, barrel running bottom-left to
# top-right:  u grows along the barrel (0..62), v is the signed cross offset.
function Get-UV([int]$X, [int]$Y) { ,@(($X + (31 - $Y)), ($X - (31 - $Y))) }

# ---------- positron_rifle.png (32x32) ----------
# Long-barrel anti-Angel sniper: stock, receiver with grip, glowing positron
# cell, scope, thin barrel, muzzle brake.
$k = @(255, 26, 28, 36)     # outline
$g = @(255, 88, 96, 112)    # gunmetal
$G = @(255, 58, 64, 78)     # dark gunmetal
$L = @(255, 172, 182, 200)  # light metal
$W = @(255, 226, 232, 244)  # highlight
$o = @(255, 255, 118, 24)   # positron cell
$Y = @(255, 255, 214, 106)  # cell core
$r = @(255, 214, 40, 40)    # NERV red accent

$bmp = New-Canvas 32
for ($y = 0; $y -lt 32; $y++) {
    for ($x = 0; $x -lt 32; $x++) {
        $uv = Get-UV $x $y
        $u = $uv[0]; $v = $uv[1]
        $c = $null

        if ($u -ge 4 -and $u -le 16 -and [Math]::Abs($v) -le 4) {                 # stock
            $c = $g
            if ($u -le 6 -or [Math]::Abs($v) -eq 4) { $c = $k }
            elseif ($v -eq -3) { $c = $L }                                        # top light edge
            elseif ($v -ge 2) { $c = $G }
        }
        elseif ($u -gt 16 -and $u -le 32 -and [Math]::Abs($v) -le 5) {            # receiver
            $c = $g
            if ([Math]::Abs($v) -ge 5) { $c = $k }
            elseif ($v -eq -4) { $c = $L }
            elseif ($v -ge 3) { $c = $G }
            if ($u -ge 24 -and $u -le 28 -and $v -ge -1 -and $v -le 1) {          # positron cell window
                $c = $o
                if ($u -ge 25 -and $u -le 27 -and $v -eq 0) { $c = $Y }
            }
            if ($u -ge 18 -and $u -le 20 -and $v -eq -2) { $c = $r }              # NERV accent stripe
        }
        elseif ($u -gt 20 -and $u -le 26 -and $v -gt 5 -and $v -le 11) {          # grip
            $c = $G
            if ($v -eq 11 -or $u -le 22) { $c = $k }
        }
        elseif ($u -gt 32 -and $u -le 52 -and [Math]::Abs($v) -le 2) {            # barrel
            $c = $L
            if ([Math]::Abs($v) -eq 2) { $c = $k }
            elseif ($v -eq -1) { $c = $W }
        }
        elseif ($u -gt 52 -and $u -le 58 -and [Math]::Abs($v) -le 3) {            # muzzle brake
            $c = $G
            if ([Math]::Abs($v) -eq 3 -or $u -ge 57) { $c = $k }
            elseif ($v -eq -2) { $c = $L }
        }
        elseif ($u -ge 20 -and $u -le 30 -and $v -ge -9 -and $v -le -6) {         # scope
            $c = $g
            if ($v -eq -9 -or $v -eq -6 -or $u -le 21) { $c = $k }
            if ($u -ge 28 -and $v -eq -7) { $c = $Y }                             # lens glint
        }

        if ($null -ne $c) { Set-Px $bmp $x $y $c }
    }
}
$bmp.Save("$root\item\positron_rifle.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote item/positron_rifle.png (32x32)"

# ---------- core_fragment.png (32x32) ----------
# Shard of an Angel core: blood-red crystal, bright fracture face, dark flank.
$k2 = @(255, 64, 10, 14)
$R  = @(255, 226, 34, 42)
$d  = @(255, 148, 16, 22)
$D2 = @(255, 106, 12, 18)
$W2 = @(255, 255, 232, 230)
$P  = @(255, 255, 120, 130)

$bmp = New-Canvas 32
for ($y = 0; $y -lt 32; $y++) {
    for ($x = 0; $x -lt 32; $x++) {
        $uv = Get-UV $x $y
        $u = $uv[0]; $v = $uv[1]
        if ($u -lt 10 -or $u -gt 52) { continue }
        # Teardrop width profile: widest a third of the way up the shard.
        $t = ($u - 10) / 42.0
        $w = [Math]::Round(6.0 * [Math]::Sin([Math]::PI * [Math]::Pow($t, 0.75)))
        if ($w -lt 1 -and $u -gt 12 -and $u -lt 50) { $w = 1 }
        if ([Math]::Abs($v) -gt $w) { continue }

        $c = $R
        if ([Math]::Abs($v) -ge $w) { $c = $k2 }                                  # rim
        elseif ($v -ge [Math]::Max(1, $w - 2)) { $c = $D2 }                       # dark flank
        elseif ($v -ge 0) { $c = $d }
        elseif ($v -eq -$w + 1) { $c = $P }                                       # lit fracture edge
        if (($u -ge 22 -and $u -le 30) -and ($v -eq -1 -or $v -eq -2)) { $c = $W2 } # glint
        Set-Px $bmp $x $y $c
    }
}
$bmp.Save("$root\item\core_fragment.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote item/core_fragment.png (32x32)"

# ---------- positron_cannon.png (32x32) ----------
# EVA-scale sniper cannon: longer and bulkier than the rifle, huge scope,
# twin energy cells. Same diagonal-axis technique.
$bmp = New-Canvas 32
for ($y = 0; $y -lt 32; $y++) {
    for ($x = 0; $x -lt 32; $x++) {
        $uv = Get-UV $x $y
        $u = $uv[0]; $v = $uv[1]
        $c = $null

        if ($u -ge 2 -and $u -le 14 -and [Math]::Abs($v) -le 5) {                 # heavy stock
            $c = $G
            if ($u -le 4 -or [Math]::Abs($v) -eq 5) { $c = $k }
            elseif ($v -eq -4) { $c = $L }
        }
        elseif ($u -gt 14 -and $u -le 34 -and [Math]::Abs($v) -le 6) {            # receiver block
            $c = $g
            if ([Math]::Abs($v) -ge 6) { $c = $k }
            elseif ($v -eq -5) { $c = $L }
            elseif ($v -ge 4) { $c = $G }
            if ($u -ge 20 -and $u -le 24 -and $v -ge -2 -and $v -le 2) {          # twin cells
                $c = $o
                if ($v -eq 0) { $c = $Y }
            }
            if ($u -ge 27 -and $u -le 31 -and $v -ge -2 -and $v -le 2) {
                $c = $o
                if ($v -eq 0) { $c = $Y }
            }
            if ($u -ge 16 -and $u -le 18 -and [Math]::Abs($v) -le 3) { $c = $r }  # NERV band
        }
        elseif ($u -gt 22 -and $u -le 30 -and $v -gt 6 -and $v -le 12) {          # grip
            $c = $G
            if ($v -eq 12 -or $u -le 24) { $c = $k }
        }
        elseif ($u -gt 34 -and $u -le 56 -and [Math]::Abs($v) -le 3) {            # heavy barrel
            $c = $L
            if ([Math]::Abs($v) -eq 3) { $c = $k }
            elseif ($v -eq -2) { $c = $W }
            elseif ($v -ge 1) { $c = $g }
        }
        elseif ($u -gt 56 -and $u -le 60 -and [Math]::Abs($v) -le 4) {            # muzzle
            $c = $G
            if ($u -ge 59 -or [Math]::Abs($v) -eq 4) { $c = $k }
        }
        elseif ($u -ge 16 -and $u -le 34 -and $v -ge -11 -and $v -le -7) {        # long scope
            $c = $g
            if ($v -eq -11 -or $v -eq -7 -or $u -le 17) { $c = $k }
            if ($u -ge 31 -and $v -ge -10 -and $v -le -8) { $c = $Y }             # lens
        }

        if ($null -ne $c) { Set-Px $bmp $x $y $c }
    }
}
$bmp.Save("$root\item\positron_cannon.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote item/positron_cannon.png (32x32)"

# ---------- eva_unit01.png (256x256 GeckoLib sheet) ----------
# Box-UV regions per cube; table MUST match geo/eva_unit01.geo.json uv origins.
# Each region gets its part colour + vertical shading + sparse panel seams.
$bmp = New-Object System.Drawing.Bitmap(256, 256)

function Fill-Region([int]$U, [int]$V, [int]$W, [int]$H, [int[]]$Rgb, [double]$Seams) {
    for ($y = 0; $y -lt $H; $y++) {
        for ($x = 0; $x -lt $W; $x++) {
            $shade = 1.0 - 0.18 * ($y / [Math]::Max(1, $H)) - 0.03 * (($x * 5 + $y * 3) % 4) / 4.0
            if ($Seams -gt 0 -and (($y % 9) -eq 4 -or ($x % 14) -eq 7)) { $shade -= $Seams }
            $r = [Math]::Max(0, [Math]::Min(255, [int]($Rgb[0] * $shade)))
            $g = [Math]::Max(0, [Math]::Min(255, [int]($Rgb[1] * $shade)))
            $b = [Math]::Max(0, [Math]::Min(255, [int]($Rgb[2] * $shade)))
            $bmp.SetPixel($U + $x, $V + $y, [System.Drawing.Color]::FromArgb(255, $r, $g, $b))
        }
    }
}

$purple  = @(96, 44, 158)
$darkpur = @(62, 28, 108)
$white2  = @(226, 228, 236)
$green2  = @(64, 240, 96)
$orange2 = @(255, 130, 20)
$metal   = @(74, 80, 94)
$lanceRed = @(196, 14, 28)

# purple armour
Fill-Region 0 0 72 40 $purple 0.10        # chest
Fill-Region 76 0 48 34 $purple 0.10      # spine
Fill-Region 128 0 64 24 $purple 0.10     # pelvis
Fill-Region 196 0 44 27 $purple 0.08     # skull
Fill-Region 0 44 38 52 $purple 0.10      # thigh_l
Fill-Region 40 44 38 52 $purple 0.10     # thigh_r
Fill-Region 80 44 34 49 $purple 0.10     # shin_l
Fill-Region 116 44 34 49 $purple 0.10    # shin_r
Fill-Region 152 44 30 36 $purple 0.08    # upper_arm_l
Fill-Region 184 44 30 36 $purple 0.08    # upper_arm_r
Fill-Region 216 44 30 38 $purple 0.08    # forearm_l
Fill-Region 0 100 30 38 $purple 0.08     # forearm_r
# dark joints
Fill-Region 32 100 36 20 $darkpur 0.0    # hand_l
Fill-Region 70 100 36 20 $darkpur 0.0    # hand_r
Fill-Region 108 100 52 21 $darkpur 0.06  # foot_l
Fill-Region 162 100 52 21 $darkpur 0.06  # foot_r
# white parts
Fill-Region 0 140 46 30 $white2 0.08     # pylon_l
Fill-Region 48 140 46 30 $white2 0.08    # pylon_r
Fill-Region 180 140 8 28 $white2 0.0     # horn
Fill-Region 190 140 16 30 $white2 0.05   # knife blade
# glow greens
Fill-Region 96 140 18 9 $green2 0.0      # core
Fill-Region 116 140 40 6 $green2 0.0     # chest V
Fill-Region 160 140 8 3 $green2 0.0      # eye_l
Fill-Region 170 140 8 3 $green2 0.0      # eye_r
# orange jaw
Fill-Region 96 152 18 9 $orange2 0.0     # jaw guard
# cannon (barrel modelled along the arm axis; box uv at 120,158)
Fill-Region 120 158 36 96 $metal 0.06    # barrel box uv
Fill-Region 208 140 36 18 $metal 0.05    # scope
# energy band across the barrel region for flavour
Fill-Region 128 200 20 8 $orange2 0.0
# Longinus shaft/forks. Each long cube repeats this compact red box-UV area.
Fill-Region 0 172 96 78 $lanceRed 0.04

$bmp.Save("$root\entity\eva_unit01.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote entity/eva_unit01.png (256x256)"

# ---------- eva_unit00.png (original Project SEELE variant) ----------
$bmp = New-Object System.Drawing.Bitmap(256, 256)
$unit00 = @(222, 142, 34)
$unit00dark = @(122, 68, 20)
foreach ($region in @(
    @(0,0,72,40), @(76,0,48,34), @(128,0,64,24), @(196,0,44,27),
    @(0,44,38,52), @(40,44,38,52), @(80,44,34,49), @(116,44,34,49),
    @(152,44,30,36), @(184,44,30,36), @(216,44,30,38), @(0,100,30,38)
)) { Fill-Region $region[0] $region[1] $region[2] $region[3] $unit00 0.10 }
Fill-Region 32 100 36 20 $unit00dark 0.0
Fill-Region 70 100 36 20 $unit00dark 0.0
Fill-Region 108 100 52 21 $unit00dark 0.06
Fill-Region 162 100 52 21 $unit00dark 0.06
Fill-Region 0 140 46 30 $white2 0.08
Fill-Region 48 140 46 30 $white2 0.08
Fill-Region 160 140 18 8 $r 0.0
Fill-Region 96 140 18 9 $green2 0.0
Fill-Region 190 140 16 30 $white2 0.05
Fill-Region 120 158 36 96 $metal 0.06
Fill-Region 208 140 36 18 $metal 0.05
$bmp.Save("$root\entity\eva_unit00.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote entity/eva_unit00.png (256x256)"

# ---------- eva_unit02.png (original Project SEELE variant) ----------
$bmp = New-Object System.Drawing.Bitmap(256, 256)
$unit02 = @(184, 32, 42)
$unit02dark = @(92, 16, 24)
foreach ($region in @(
    @(0,0,72,40), @(76,0,48,34), @(128,0,64,24), @(196,0,44,27),
    @(0,44,38,52), @(40,44,38,52), @(80,44,34,49), @(116,44,34,49),
    @(152,44,30,36), @(184,44,30,36), @(216,44,30,38), @(0,100,30,38)
)) { Fill-Region $region[0] $region[1] $region[2] $region[3] $unit02 0.11 }
Fill-Region 32 100 36 20 $unit02dark 0.0
Fill-Region 70 100 36 20 $unit02dark 0.0
Fill-Region 108 100 52 21 $unit02dark 0.06
Fill-Region 162 100 52 21 $unit02dark 0.06
Fill-Region 0 140 46 30 $white2 0.08
Fill-Region 48 140 46 30 $white2 0.08
Fill-Region 180 140 8 28 $orange2 0.0
Fill-Region 190 140 16 30 $white2 0.05
Fill-Region 96 140 18 9 $green2 0.0
Fill-Region 116 140 40 6 $orange2 0.0
Fill-Region 160 140 18 9 $green2 0.0
Fill-Region 170 140 18 9 $green2 0.0
Fill-Region 96 152 18 9 $orange2 0.0
Fill-Region 120 158 36 96 $metal 0.06
Fill-Region 208 140 36 18 $metal 0.05
$bmp.Save("$root\entity\eva_unit02.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote entity/eva_unit02.png (256x256)"

# ---------- ramiel.png (32x32 entity gradient) ----------
# Near-white blue with fine facet seams; renderer vertex colors do the tinting.
$bmp = New-Canvas 32
for ($y = 0; $y -lt 32; $y++) {
    for ($x = 0; $x -lt 32; $x++) {
        $v2 = 240 - $y * 2 - (($x + $y) % 3)
        if ((($x + $y) % 8) -eq 0) { $v2 -= 12 }                                  # facet seams
        if ((($x - $y + 64) % 16) -eq 0) { $v2 -= 6 }                             # cross seams
        Set-Px $bmp $x $y @(255, [Math]::Max(0, $v2 - 10), [Math]::Max(0, $v2 - 2), 255)
    }
}
$bmp.Save("$root\entity\ramiel.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote entity/ramiel.png (32x32)"
