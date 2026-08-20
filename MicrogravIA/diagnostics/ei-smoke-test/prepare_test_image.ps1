param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$ExpectedLabel,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$targetWidth = 96
$targetHeight = 96
$fractionBits = 14
$fractionValue = 1 -shl $fractionBits
$fractionMask = $fractionValue - 1

$resolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
$sourceDisplay = 'ImagensParaIA/' + [System.IO.Path]::GetFileName($resolvedSource)
$bitmap = [System.Drawing.Bitmap]::FromFile($resolvedSource)

try {
    $sourceWidth = $bitmap.Width
    $sourceHeight = $bitmap.Height

    if ($sourceWidth -gt $sourceHeight) {
        $cropWidth = [int](($targetWidth * $sourceHeight) / $targetHeight)
        $cropHeight = $sourceHeight
    }
    else {
        $cropWidth = $sourceWidth
        $cropHeight = [int](($targetHeight * $sourceWidth) / $targetWidth)
    }

    $cropX = [int](($sourceWidth - $cropWidth) / 2)
    $cropY = [int](($sourceHeight - $cropHeight) / 2)
    $sourceXFraction = [uint32](($cropWidth * $fractionValue) / $targetWidth)
    $sourceYFraction = [uint32](($cropHeight * $fractionValue) / $targetHeight)

    $rgb = [byte[]]::new($targetWidth * $targetHeight * 3)
    $destinationIndex = 0
    [uint32]$sourceYAccumulator = 0

    for ($y = 0; $y -lt $targetHeight; ++$y) {
        $sourceY = [int]($sourceYAccumulator -shr $fractionBits)
        $yFraction = [uint32]($sourceYAccumulator -band $fractionMask)
        $nextYFraction = [uint32]($fractionValue - $yFraction)
        $sourceYAccumulator += $sourceYFraction

        [uint32]$sourceXAccumulator = 0

        for ($x = 0; $x -lt $targetWidth; ++$x) {
            $sourceX = [int]($sourceXAccumulator -shr $fractionBits)
            $xFraction = [uint32]($sourceXAccumulator -band $fractionMask)
            $nextXFraction = [uint32]($fractionValue - $xFraction)
            $sourceXAccumulator += $sourceXFraction

            $pixel00 = $bitmap.GetPixel($cropX + $sourceX, $cropY + $sourceY)
            $pixel10 = $bitmap.GetPixel($cropX + $sourceX + 1, $cropY + $sourceY)
            $pixel01 = $bitmap.GetPixel($cropX + $sourceX, $cropY + $sourceY + 1)
            $pixel11 = $bitmap.GetPixel($cropX + $sourceX + 1, $cropY + $sourceY + 1)

            foreach ($channel in @('R', 'G', 'B')) {
                [int64]$top =
                    (([int64]$pixel00.$channel * $nextXFraction) +
                     ([int64]$pixel10.$channel * $xFraction) +
                     ($fractionValue / 2)) -shr $fractionBits
                [int64]$bottom =
                    (([int64]$pixel01.$channel * $nextXFraction) +
                     ([int64]$pixel11.$channel * $xFraction) +
                     ($fractionValue / 2)) -shr $fractionBits
                [int64]$value =
                    (($top * $nextYFraction) +
                     ($bottom * $yFraction) +
                     ($fractionValue / 2)) -shr $fractionBits

                $rgb[$destinationIndex++] = [byte]$value
            }
        }
    }

    $sourceHash = (Get-FileHash -LiteralPath $resolvedSource -Algorithm SHA256).Hash
    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('#pragma once')
    $lines.Add('')
    $lines.Add('#include <Arduino.h>')
    $lines.Add('#include <cstddef>')
    $lines.Add('#include <cstdint>')
    $lines.Add('')
    $lines.Add('namespace diagnostic {')
    $lines.Add('')
    $lines.Add(('constexpr size_t kTestImageWidth = {0};' -f $targetWidth))
    $lines.Add(('constexpr size_t kTestImageHeight = {0};' -f $targetHeight))
    $lines.Add(('constexpr size_t kTestImageChannels = 3;'))
    $lines.Add(('constexpr char kTestImageExpectedLabel[] = "{0}";' -f $ExpectedLabel))
    $lines.Add(('constexpr char kTestImageSource[] = "{0}";' -f $sourceDisplay))
    $lines.Add(('constexpr char kTestImageSourceSha256[] = "{0}";' -f $sourceHash))
    $lines.Add(('constexpr size_t kTestImageCropX = {0};' -f $cropX))
    $lines.Add(('constexpr size_t kTestImageCropY = {0};' -f $cropY))
    $lines.Add(('constexpr size_t kTestImageCropWidth = {0};' -f $cropWidth))
    $lines.Add(('constexpr size_t kTestImageCropHeight = {0};' -f $cropHeight))
    $lines.Add('')
    $lines.Add('static const uint8_t kTestImageRgb[')
    $lines.Add('    kTestImageWidth * kTestImageHeight * kTestImageChannels] PROGMEM = {')

    for ($offset = 0; $offset -lt $rgb.Length; $offset += 12) {
        $count = [Math]::Min(12, $rgb.Length - $offset)
        $values = for ($index = 0; $index -lt $count; ++$index) {
            '0x{0:X2}' -f $rgb[$offset + $index]
        }
        $lines.Add(('    {0},' -f ($values -join ', ')))
    }

    $lines.Add('};')
    $lines.Add('')
    $lines.Add('}  // namespace diagnostic')
    $lines.Add('')

    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
    [System.IO.File]::WriteAllLines(
        $resolvedOutput,
        $lines,
        [System.Text.UTF8Encoding]::new($false))

    [PSCustomObject]@{
        Source = $resolvedSource
        SourceWidth = $sourceWidth
        SourceHeight = $sourceHeight
        CropX = $cropX
        CropY = $cropY
        CropWidth = $cropWidth
        CropHeight = $cropHeight
        OutputWidth = $targetWidth
        OutputHeight = $targetHeight
        OutputBytes = $rgb.Length
        ExpectedLabel = $ExpectedLabel
        SourceSHA256 = $sourceHash
        Output = $resolvedOutput
    } | Format-List
}
finally {
    $bitmap.Dispose()
}
