# Generates the subtle, neutral edge texture for NERV structural glass.
# The pane interior is fully transparent; only a faint one-pixel frame remains.

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root "src/main/resources/assets/projectseele/textures/block/clear_glass.png"
$bitmap = New-Object System.Drawing.Bitmap 16, 16,
    ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)

for ($y = 0; $y -lt 16; $y++) {
    for ($x = 0; $x -lt 16; $x++) {
        $edge = $x -eq 0 -or $x -eq 15 -or $y -eq 0 -or $y -eq 15
        $corner = ($x -eq 0 -or $x -eq 15) -and ($y -eq 0 -or $y -eq 15)
        $alpha = if ($corner) { 28 } elseif ($edge) { 18 } else { 0 }
        $bitmap.SetPixel($x, $y,
            [System.Drawing.Color]::FromArgb($alpha, 236, 244, 244))
    }
}

$bitmap.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
Write-Output "Wrote $output"
