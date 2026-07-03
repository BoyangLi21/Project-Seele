Add-Type -AssemblyName System.Drawing

$root = 'F:\eva\src\main\resources\assets\projectseele\textures'
New-Item -ItemType Directory -Force "$root\item" | Out-Null
New-Item -ItemType Directory -Force "$root\entity" | Out-Null

# NOTE: PowerShell hashtable keys are case-insensitive, so every palette
# character must differ by more than case.
function Save-PixelArt([string]$path, [string[]]$rows, [hashtable]$palette) {
    $h = $rows.Count
    $w = $rows[0].Length
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    for ($y = 0; $y -lt $h; $y++) {
        $row = $rows[$y]
        for ($x = 0; $x -lt $w; $x++) {
            $ch = $row[$x].ToString()
            if ($palette.ContainsKey($ch)) {
                $c = $palette[$ch]
                $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($c[0], $c[1], $c[2], $c[3]))
            } else {
                $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(0, 0, 0, 0))
            }
        }
    }
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "wrote $path ($w x $h)"
}

# --- Positron Rifle (sword-style diagonal: muzzle top-right, stock bottom-left)
#     k=outline  g=gunmetal  L=light metal barrel  o=orange cell  Y=bright cell ---
$rifleRows = @(
    '................',
    '..............kk',
    '.............kLk',
    '............kLk.',
    '...........kLk..',
    '..........kLk...',
    '....kk...kLk....',
    '...koYk.kLk.....',
    '...koYkkLk......',
    '..kkggggkk......',
    '..kgggggk.......',
    '.kggkkggk.......',
    '.kgk..kgk.......',
    'kgk...kk........',
    'kkk.............',
    '................'
)
$riflePalette = @{
    'k' = @(255, 30, 32, 40)
    'g' = @(255, 90, 98, 114)
    'L' = @(255, 168, 178, 196)
    'o' = @(255, 255, 120, 30)
    'Y' = @(255, 255, 208, 96)
}
Save-PixelArt "$root\item\positron_rifle.png" $rifleRows $riflePalette

# --- Angel Core Fragment (red crystal shard)
#     k=outline  R=red  d=dark red  W=white highlight ---
$fragRows = @(
    '................',
    '.........kk.....',
    '........kRWk....',
    '.......kRRWk....',
    '......kRRRk.....',
    '......kRRRk.....',
    '.....kRRRk......',
    '....kRRRk.......',
    '....kRRk........',
    '...kRRk.........',
    '..kRdk..........',
    '..kddk..........',
    '.kdk............',
    '.kk.............',
    '................',
    '................'
)
$fragPalette = @{
    'k' = @(255, 70, 12, 16)
    'R' = @(255, 227, 36, 43)
    'd' = @(255, 150, 18, 24)
    'W' = @(255, 255, 235, 235)
}
Save-PixelArt "$root\item\core_fragment.png" $fragRows $fragPalette

# --- Ramiel body texture: near-white blue gradient with faint facet lines.
#     Vertex colors in the renderer supply the actual blue / red tinting. ---
$bmp = New-Object System.Drawing.Bitmap(16, 16)
for ($y = 0; $y -lt 16; $y++) {
    for ($x = 0; $x -lt 16; $x++) {
        $v = 235 - $y * 3 - (($x + $y) % 4)
        if ((($x + $y) % 8) -eq 0) { $v -= 14 }
        $bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, $v - 8, $v, 255))
    }
}
$bmp.Save("$root\entity\ramiel.png", [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "wrote $root\entity\ramiel.png (16 x 16)"
