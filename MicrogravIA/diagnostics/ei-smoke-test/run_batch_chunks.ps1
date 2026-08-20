param(
    [Parameter(Mandatory = $true)]
    [string]$ImageRoot,

    [string]$InventoryPath = (Join-Path $PSScriptRoot 'batch_inventory.csv'),
    [string]$Port = 'COM4',
    [int]$BaudRate = 460800,
    [int]$StartIndex = 0,
    [int]$ChunkSize = 20,
    [int]$MaxAttempts = 3,
    [string]$RunName = 'batch_final',
    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

if ($ChunkSize -le 0) {
    throw 'ChunkSize must be greater than zero.'
}
if ($MaxAttempts -le 0) {
    throw 'MaxAttempts must be greater than zero.'
}

$runnerPath = Join-Path $PSScriptRoot 'run_batch_validation.ps1'
$resolvedInventory = (Resolve-Path -LiteralPath $InventoryPath).Path
$inventory = @(Import-Csv -LiteralPath $resolvedInventory)
if ($StartIndex -lt 0 -or $StartIndex -ge $inventory.Count) {
    throw "StartIndex is outside the inventory: $StartIndex"
}
$resultsPath = Join-Path $PSScriptRoot ($RunName + '_results.csv')
$boxesPath = Join-Path $PSScriptRoot ($RunName + '_boxes.csv')
$runsPath = Join-Path $PSScriptRoot ($RunName + '_runs.csv')
$serialPath = Join-Path $PSScriptRoot ($RunName + '_serial.log')

foreach ($path in @($resultsPath, $boxesPath, $runsPath, $serialPath)) {
    if ((Test-Path -LiteralPath $path) -and -not $Overwrite) {
        throw "Output already exists: $path. Use -Overwrite to replace it."
    }
    if ((Test-Path -LiteralPath $path) -and $Overwrite) {
        Remove-Item -LiteralPath $path -Force
    }
}

$allResults = [System.Collections.Generic.List[object]]::new()
$allBoxes = [System.Collections.Generic.List[object]]::new()
$allRuns = [System.Collections.Generic.List[object]]::new()

for ($chunkStartIndex = $StartIndex; $chunkStartIndex -lt $inventory.Count; $chunkStartIndex += $ChunkSize) {
    $count = [Math]::Min($ChunkSize, $inventory.Count - $chunkStartIndex)
    $firstId = $chunkStartIndex + 1
    $lastId = $chunkStartIndex + $count
    $completed = $false

    for ($attempt = 1; $attempt -le $MaxAttempts -and -not $completed; ++$attempt) {
        $chunkName = '{0}_chunk_{1:D4}_{2:D4}_attempt{3}' -f $RunName, $firstId, $lastId, $attempt
        Write-Output "=== Chunk $firstId-$lastId, attempt $attempt/$MaxAttempts ==="

        $arguments = @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', $runnerPath,
            '-ImageRoot', $ImageRoot,
            '-InventoryPath', $resolvedInventory,
            '-Port', $Port,
            '-BaudRate', $BaudRate,
            '-RunName', $chunkName,
            '-StartIndex', $chunkStartIndex,
            '-Limit', $count,
            '-Overwrite'
        )

        $savedErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & powershell.exe @arguments 2>&1 | ForEach-Object { Write-Output $_ }
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $savedErrorActionPreference
        $chunkResultsPath = Join-Path $PSScriptRoot ($chunkName + '_results.csv')
        $chunkBoxesPath = Join-Path $PSScriptRoot ($chunkName + '_boxes.csv')
        $chunkSerialPath = Join-Path $PSScriptRoot ($chunkName + '_serial.log')
        $chunkResults = if (Test-Path -LiteralPath $chunkResultsPath) {
            @(Import-Csv -LiteralPath $chunkResultsPath)
        }
        else {
            @()
        }

        $allRuns.Add([PSCustomObject]@{
            FirstId = $firstId
            LastId = $lastId
            Attempt = $attempt
            ExitCode = $exitCode
            CompletedRows = $chunkResults.Count
            Accepted = ($exitCode -eq 0 -and $chunkResults.Count -eq $count)
            ResultsFile = [System.IO.Path]::GetFileName($chunkResultsPath)
            SerialFile = [System.IO.Path]::GetFileName($chunkSerialPath)
        })

        if ($exitCode -eq 0 -and $chunkResults.Count -eq $count) {
            foreach ($row in $chunkResults) {
                $allResults.Add($row)
            }
            if (Test-Path -LiteralPath $chunkBoxesPath) {
                foreach ($box in @(Import-Csv -LiteralPath $chunkBoxesPath)) {
                    $allBoxes.Add($box)
                }
            }
            Add-Content -LiteralPath $serialPath -Value "===== ACCEPTED CHUNK $firstId-$lastId ATTEMPT $attempt =====" -Encoding UTF8
            Get-Content -LiteralPath $chunkSerialPath | Add-Content -LiteralPath $serialPath -Encoding UTF8
            $completed = $true
        }
        else {
            Write-Warning "Chunk $firstId-$lastId attempt $attempt failed: exit=$exitCode rows=$($chunkResults.Count)/$count"
        }
    }

    if (-not $completed) {
        $allRuns | Export-Csv -LiteralPath $runsPath -NoTypeInformation -Encoding UTF8
        throw "Chunk $firstId-$lastId did not complete after $MaxAttempts attempts."
    }

    $allResults | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Encoding UTF8
    if ($allBoxes.Count -gt 0) {
        $allBoxes | Export-Csv -LiteralPath $boxesPath -NoTypeInformation -Encoding UTF8
    }
    $allRuns | Export-Csv -LiteralPath $runsPath -NoTypeInformation -Encoding UTF8
    Write-Output "Accepted through image $lastId/$($inventory.Count)."
}

$expectedResultCount = $inventory.Count - $StartIndex
if ($allResults.Count -ne $expectedResultCount) {
    throw "Final result count mismatch: $($allResults.Count)/$expectedResultCount"
}

Write-Output "BATCH_COMPLETE|images=$($allResults.Count)|boxes=$($allBoxes.Count)|runs=$($allRuns.Count)"
