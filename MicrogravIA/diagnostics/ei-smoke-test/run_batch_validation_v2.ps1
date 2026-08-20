param(
    [Parameter(Mandatory = $true)]
    [string]$ImageRoot,

    [string]$InventoryPath = (Join-Path $PSScriptRoot 'results_v2\batch_v2_inventory.csv'),

    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'results_v2'),
    [string]$Port = 'COM4',
    [int]$BaudRate = 460800,
    [string]$RunName = 'batch_v2',
    [int]$StartIndex = 0,
    [int]$Limit = 0,
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'EiImagePreprocessV2.psm1') -Force

function ConvertFrom-EiStructuredLine {
    param([string]$Line)

    $fields = @{}
    $parts = $Line.Split('|')
    for ($index = 1; $index -lt $parts.Length; ++$index) {
        $separator = $parts[$index].IndexOf('=')
        if ($separator -gt 0) {
            $key = $parts[$index].Substring(0, $separator)
            $value = $parts[$index].Substring($separator + 1)
            $fields[$key] = $value
        }
    }
    return $fields
}

function Read-EiLine {
    param(
        [System.IO.Ports.SerialPort]$Serial,
        [datetime]$Deadline
    )

    while ([DateTime]::UtcNow -lt $Deadline) {
        try {
            return $Serial.ReadLine().Trim()
        }
        catch [System.TimeoutException] {
        }
    }
    throw 'Serial response timeout.'
}

function New-ImagePacketHeader {
    param(
        [uint32]$ImageId,
        [byte]$ExpectedClass,
        [uint32]$PayloadLength,
        [uint32]$Crc32
    )

    $stream = [System.IO.MemoryStream]::new()
    $writer = [System.IO.BinaryWriter]::new($stream)
    try {
        $writer.Write([uint32]0x474D4945)
        $writer.Write($ImageId)
        $writer.Write($ExpectedClass)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write($PayloadLength)
        $writer.Write($Crc32)
        $writer.Flush()
        return $stream.ToArray()
    }
    finally {
        $writer.Dispose()
        $stream.Dispose()
    }
}

function Write-EiPayload {
    param(
        [System.IO.Ports.SerialPort]$Serial,
        [byte[]]$Data
    )

    $chunkSize = 128
    $pauseTicks = [long]([System.Diagnostics.Stopwatch]::Frequency * 4 / 1000)
    for ($offset = 0; $offset -lt $Data.Length; $offset += $chunkSize) {
        $count = [Math]::Min($chunkSize, $Data.Length - $offset)
        $Serial.Write($Data, $offset, $count)
        $pauseStarted = [System.Diagnostics.Stopwatch]::GetTimestamp()
        while (([System.Diagnostics.Stopwatch]::GetTimestamp() - $pauseStarted) -lt $pauseTicks) {
        }
    }
}

function Write-CsvRecord {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        $Record | Export-Csv -LiteralPath $Path -NoTypeInformation -Append -Encoding UTF8
    }
    else {
        $Record | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding UTF8
    }
}

$resolvedImageRoot = (Resolve-Path -LiteralPath $ImageRoot).Path
$resolvedInventory = (Resolve-Path -LiteralPath $InventoryPath).Path
$resolvedOutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
$inventory = @(Import-Csv -LiteralPath $resolvedInventory)

if ($StartIndex -lt 0 -or $StartIndex -ge $inventory.Count) {
    throw "StartIndex is outside the inventory: $StartIndex"
}

$inventory = @($inventory | Select-Object -Skip $StartIndex)

if ($Limit -gt 0) {
    $inventory = @($inventory | Select-Object -First $Limit)
}

if ($inventory.Count -eq 0) {
    throw 'The inventory is empty.'
}

$resultsPath = Join-Path $resolvedOutputDirectory ($RunName + '_results.csv')
$boxesPath = Join-Path $resolvedOutputDirectory ($RunName + '_boxes.csv')
$serialLogPath = Join-Path $resolvedOutputDirectory ($RunName + '_serial.log')

foreach ($outputPath in @($resultsPath, $boxesPath, $serialLogPath)) {
    if ((Test-Path -LiteralPath $outputPath) -and -not $Overwrite) {
        throw "Output already exists: $outputPath. Use -Overwrite to replace it."
    }
}

if ($Overwrite) {
    foreach ($outputPath in @($resultsPath, $boxesPath, $serialLogPath)) {
        if (Test-Path -LiteralPath $outputPath) {
            Remove-Item -LiteralPath $outputPath -Force
        }
    }
}

$serialLog = [System.IO.StreamWriter]::new(
    $serialLogPath,
    $false,
    [System.Text.UTF8Encoding]::new($false))
$serialLog.AutoFlush = $true

$serial = [System.IO.Ports.SerialPort]::new(
    $Port,
    $BaudRate,
    [System.IO.Ports.Parity]::None,
    8,
    [System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = 250
$serial.WriteTimeout = 120000
$serial.NewLine = "`n"
$serial.DtrEnable = $false
$serial.RtsEnable = $false

$startedAt = [DateTime]::UtcNow
$processedCount = 0
$previousHeap = $null
$previousPsram = $null
$heapDecreaseStreak = 0
$psramDecreaseStreak = 0

try {
    $serial.Open()
    Start-Sleep -Milliseconds 250
    $serial.DiscardInBuffer()
    $serial.DtrEnable = $false
    $serial.RtsEnable = $true
    Start-Sleep -Milliseconds 150
    $serial.RtsEnable = $false

    $ready = $false
    $readyDeadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $readyDeadline) {
        $line = Read-EiLine -Serial $serial -Deadline $readyDeadline
        $serialLog.WriteLine($line)
        if ($line.StartsWith('EI_BATCH_READY|')) {
            $readyFields = ConvertFrom-EiStructuredLine $line
            if ($readyFields['width'] -ne '160' -or
                $readyFields['height'] -ne '160' -or
                $readyFields['channels'] -ne '3' -or
                $readyFields['bytes'] -ne '76800' -or
                $readyFields['resize'] -ne 'FIT_LONGEST') {
                throw "Unexpected runner dimensions: $line"
            }
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        throw 'EI_BATCH_READY was not received.'
    }

    Write-Output "Runner ready on $Port at $BaudRate baud. Images: $($inventory.Count)"

    for ($inventoryIndex = 0; $inventoryIndex -lt $inventory.Count; ++$inventoryIndex) {
        $record = $inventory[$inventoryIndex]
        $imageId = [uint32]($StartIndex + $inventoryIndex + 1)
        $sourcePath = Join-Path $resolvedImageRoot $record.File
        $actualHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
        if ($actualHash -ne $record.SHA256) {
            throw "Image hash changed after inventory: $($record.File)"
        }

        $prepared = ConvertTo-EiV2Rgb888 -SourcePath $sourcePath
        if ($prepared.Rgb.Length -ne 76800) {
            throw "Unexpected RGB byte count for $($record.File): $($prepared.Rgb.Length)"
        }
        if ($prepared.SourceWidth -ne [int]$record.Width -or
            $prepared.SourceHeight -ne [int]$record.Height) {
            throw "Image dimensions changed after inventory: $($record.File)"
        }

        $expectedClass = if ($record.Expected -eq '031') { [byte]0 } elseif ($record.Expected -eq '045') { [byte]1 } else { throw "Unexpected label: $($record.Expected)" }
        $crc32 = Get-EiV2Crc32 -Data $prepared.Rgb
        $header = New-ImagePacketHeader `
            -ImageId $imageId `
            -ExpectedClass $expectedClass `
            -PayloadLength ([uint32]$prepared.Rgb.Length) `
            -Crc32 $crc32

        $serialLog.WriteLine(
            "PC_IMAGE|id=$imageId|file=$($record.File)|expected=$($record.Expected)|sha256=$actualHash|crc32=$('{0:X8}' -f $crc32)|resize=$($prepared.ResizeWidth)x$($prepared.ResizeHeight)|pad=$($prepared.PadX),$($prepared.PadY)")
        $serial.Write($header, 0, $header.Length)
        Write-EiPayload -Serial $serial -Data $prepared.Rgb

        $summary = $null
        $imageBoxes = [System.Collections.Generic.List[object]]::new()
        $responseDeadline = [DateTime]::UtcNow.AddSeconds(150)

        while ([DateTime]::UtcNow -lt $responseDeadline) {
            $line = Read-EiLine -Serial $serial -Deadline $responseDeadline
            $serialLog.WriteLine($line)

            if ($line -match 'Guru Meditation|watchdog|panic|alloc.*fail|rst:') {
                throw "Runtime failure while processing $($record.File): $line"
            }
            if ($line.StartsWith('EI_FATAL|')) {
                throw "Runner fatal error for $($record.File): $line"
            }
            if ($line.StartsWith('EI_BATCH_READY|')) {
                throw "Unexpected runner reset while processing $($record.File)."
            }
            if ($line.StartsWith('EI_RESULT|')) {
                $fields = ConvertFrom-EiStructuredLine $line
                if ([uint32]$fields['id'] -eq $imageId) {
                    $summary = $fields
                }
            }
            elseif ($line.StartsWith('EI_BOX|')) {
                $fields = ConvertFrom-EiStructuredLine $line
                if ([uint32]$fields['id'] -eq $imageId) {
                    $imageBoxes.Add([PSCustomObject]@{
                        Id = $imageId
                        File = $record.File
                        Expected = $record.Expected
                        Index = [uint32]$fields['index']
                        Label = $fields['label']
                        Confidence = [double]::Parse($fields['confidence'], [System.Globalization.CultureInfo]::InvariantCulture)
                        X = [uint32]$fields['x']
                        Y = [uint32]$fields['y']
                        W = [uint32]$fields['w']
                        H = [uint32]$fields['h']
                    })
                }
            }
            elseif ($line.StartsWith('EI_DONE|')) {
                $fields = ConvertFrom-EiStructuredLine $line
                if ([uint32]$fields['id'] -eq $imageId) {
                    break
                }
            }
        }

        if ($null -eq $summary) {
            throw "No EI_RESULT received for $($record.File)."
        }
        if ($summary['status'] -ne 'OK' -or [int]$summary['error'] -ne 0) {
            throw "Edge Impulse error for $($record.File): status=$($summary['status']) error=$($summary['error'])"
        }
        if ([uint32]$summary['valid_boxes'] -ne $imageBoxes.Count) {
            throw "Box count mismatch for $($record.File)."
        }

        $labels = @($imageBoxes | Select-Object -ExpandProperty Label -Unique | Sort-Object)
        if ($labels.Count -eq 0) {
            $classification = 'SEM_DETECCAO'
            $detected = 'NONE'
        }
        elseif ($labels.Count -eq 1 -and $labels[0] -eq $record.Expected) {
            $classification = 'CORRETA'
            $detected = $labels[0]
        }
        elseif ($labels.Count -eq 1) {
            $classification = 'CONFUNDIDA'
            $detected = $labels[0]
        }
        else {
            $classification = 'AMBIGUA'
            $detected = $labels -join '+'
        }

        $confidence = if ($imageBoxes.Count -gt 0) {
            ($imageBoxes | Measure-Object -Property Confidence -Maximum).Maximum
        }
        else {
            0.0
        }
        $allConfidences = @($imageBoxes | ForEach-Object {
            $_.Confidence.ToString('0.000000', [System.Globalization.CultureInfo]::InvariantCulture)
        }) -join ';'

        $resultRecord = [PSCustomObject]@{
            Id = $imageId
            File = $record.File
            Expected = $record.Expected
            Detected = $detected
            Confidence = [double]$confidence
            AllConfidences = $allConfidences
            Boxes = $imageBoxes.Count
            RawBoxes = [uint32]$summary['raw_boxes']
            Result = $classification
            DspUs = [int64]$summary['dsp_us']
            InferenceUs = [int64]$summary['inference_us']
            PostprocessUs = [int64]$summary['postprocess_us']
            HeapBefore = [uint32]$summary['heap_before']
            HeapAfter = [uint32]$summary['heap_after']
            PsramBefore = [uint32]$summary['psram_before']
            PsramAfter = [uint32]$summary['psram_after']
            MinHeap = [uint32]$summary['min_heap']
            Width = [int]$record.Width
            Height = [int]$record.Height
            SHA256 = $actualHash
            Crc32 = '{0:X8}' -f $crc32
        }

        Write-CsvRecord -Record $resultRecord -Path $resultsPath
        foreach ($boxRecord in $imageBoxes) {
            Write-CsvRecord -Record $boxRecord -Path $boxesPath
        }

        $currentHeap = [uint32]$summary['heap_after']
        $currentPsram = [uint32]$summary['psram_after']
        if ($null -ne $previousHeap -and $currentHeap -lt $previousHeap) {
            ++$heapDecreaseStreak
        }
        else {
            $heapDecreaseStreak = 0
        }
        if ($null -ne $previousPsram -and $currentPsram -lt $previousPsram) {
            ++$psramDecreaseStreak
        }
        else {
            $psramDecreaseStreak = 0
        }
        if ($heapDecreaseStreak -ge 5 -or $psramDecreaseStreak -ge 5) {
            throw "Progressive memory loss detected after $($record.File)."
        }
        $previousHeap = $currentHeap
        $previousPsram = $currentPsram

        ++$processedCount
        if (($processedCount % 10) -eq 0 -or
            $classification -ne 'CORRETA' -or
            $processedCount -eq $inventory.Count) {
            Write-Output (
                '[{0}/{1}] {2} => {3}, detected={4}, confidence={5:0.000000}, boxes={6}, inference={7} us' -f
                $processedCount,
                $inventory.Count,
                $record.File,
                $classification,
                $detected,
                [double]$confidence,
                $imageBoxes.Count,
                [int64]$summary['inference_us'])
        }
    }
}
finally {
    if ($serial.IsOpen) {
        $serial.Close()
    }
    $serial.Dispose()
    $serialLog.Dispose()
}

$elapsed = [DateTime]::UtcNow - $startedAt
[PSCustomObject]@{
    Processed = $processedCount
    Requested = $inventory.Count
    Duration = $elapsed
    Results = $resultsPath
    Boxes = $boxesPath
    SerialLog = $serialLogPath
} | Format-List
