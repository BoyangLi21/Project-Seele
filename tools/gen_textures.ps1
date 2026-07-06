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

# ---------- eva_unit01.png (32x32 entity sheet) ----------
# Flat armour plate: subtle vertical gradient with darker panel seams. The
# renderer's vertex colors provide the purple/green; keep this near-white.
$bmp = New-Canvas 32
for ($y = 0; $y -lt 32; $y++) {
    for ($x = 0; $x -lt 32; $x++) {
        $v2 = 232 - $y - (($x * 7 + $y * 3) % 5)
        if (($y % 11) -eq 0 -or ($x % 13) -eq 0) { $v2 -= 16 }                    # panel seams
        Set-Px $bmp $x $y @(255, $v2, $v2, [Math]::Min(255, $v2 + 6))
    }
}
$bmp.Save("$root\entity\eva_unit01.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote entity/eva_unit01.png (32x32)"

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
