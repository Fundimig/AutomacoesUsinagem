param(
    [Parameter(Mandatory = $true)]
    [string]$ImageRoot,

    [string]$ResultsDirectory,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ResultsDirectory)) {
    $ResultsDirectory = Join-Path $PSScriptRoot 'results_v2'
}

$resolvedImageRoot = (Resolve-Path -LiteralPath $ImageRoot).Path
$resolvedResults = (Resolve-Path -LiteralPath $ResultsDirectory).Path
$problematicPath = Join-Path $resolvedResults 'batch_v2_problematic.csv'
$outputDirectory = Join-Path $resolvedResults 'audit_visual\model_inputs'
$manifestPath = Join-Path $resolvedResults 'audit_visual\model_inputs_manifest.csv'

Import-Module (Join-Path $PSScriptRoot 'EiImagePreprocessV2.psm1') -Force
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

if ((Test-Path -LiteralPath $manifestPath) -and -not $Overwrite) {
    throw "Output already exists: $manifestPath. Use -Overwrite to replace it."
}

$manifest = [System.Collections.Generic.List[object]]::new()
$rows = @(Import-Csv -LiteralPath $problematicPath)

foreach ($row in $rows) {
    $sourcePath = Join-Path $resolvedImageRoot ($row.File -replace '/', '\')
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Source image not found: $sourcePath"
    }

    $prepared = ConvertTo-EiV2Rgb888 -SourcePath $sourcePath
    if ($prepared.ResizeWidth -ne 160 -or $prepared.ResizeHeight -ne 120 -or
        $prepared.PadX -ne 0 -or $prepared.PadY -ne 20 -or
        $prepared.Rgb.Length -ne 76800) {
        throw "Unexpected preprocessing geometry for $($row.File)"
    }

    $crc32 = (Get-EiV2Crc32 -Data $prepared.Rgb).ToString('X8')
    if ($crc32 -ne $row.Crc32) {
        throw "CRC mismatch for $($row.File): expected=$($row.Crc32), actual=$crc32"
    }

    $safeName = ('{0:D4}_{1}_{2}' -f [int]$row.Id, $row.Expected,
        [System.IO.Path]::GetFileNameWithoutExtension($row.File))
    $rgbPath = Join-Path $outputDirectory ($safeName + '.rgb')
    [System.IO.File]::WriteAllBytes($rgbPath, $prepared.Rgb)

    $manifest.Add([PSCustomObject]@{
        Id = $row.Id
        File = $row.File
        Expected = $row.Expected
        Result = $row.Result
        SourceWidth = $prepared.SourceWidth
        SourceHeight = $prepared.SourceHeight
        ResizeWidth = $prepared.ResizeWidth
        ResizeHeight = $prepared.ResizeHeight
        PadX = $prepared.PadX
        PadY = $prepared.PadY
        Bytes = $prepared.Rgb.Length
        Crc32 = $crc32
        RgbFile = 'model_inputs/' + [System.IO.Path]::GetFileName($rgbPath)
    })
}

$manifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
Write-Output "PREVIEWS_EXPORTED|count=$($manifest.Count)|bytes=$((Get-ChildItem -LiteralPath $outputDirectory -Filter '*.rgb' | Measure-Object Length -Sum).Sum)|manifest=$manifestPath"
