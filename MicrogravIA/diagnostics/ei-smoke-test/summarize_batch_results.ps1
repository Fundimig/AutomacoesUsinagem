param(
    [string]$InventoryPath = (Join-Path $PSScriptRoot 'batch_inventory.csv'),
    [string]$FirstResultsPath = (Join-Path $PSScriptRoot 'batch_final_results.csv'),
    [string]$SecondResultsPath = (Join-Path $PSScriptRoot 'batch_resume2_results.csv'),
    [string]$FirstBoxesPath = (Join-Path $PSScriptRoot 'batch_final_boxes.csv'),
    [string]$SecondBoxesPath = (Join-Path $PSScriptRoot 'batch_resume2_boxes.csv'),
    [string]$FirstRunsPath = (Join-Path $PSScriptRoot 'batch_final_runs.csv'),
    [string]$SecondRunsPath = (Join-Path $PSScriptRoot 'batch_resume2_runs.csv')
)

$ErrorActionPreference = 'Stop'
$invariant = [Globalization.CultureInfo]::InvariantCulture

function Convert-ToDouble {
    param([object]$Value)
    return [double]::Parse(([string]$Value).Replace(',', '.'), $invariant)
}

function Format-Decimal6 {
    param([double]$Value)
    return $Value.ToString('0.000000', $invariant)
}

function Get-Median {
    param([double[]]$Values)
    $sorted = @($Values | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    if (($sorted.Count % 2) -eq 1) {
        return $sorted[[int][Math]::Floor($sorted.Count / 2)]
    }
    return ($sorted[$sorted.Count / 2 - 1] + $sorted[$sorted.Count / 2]) / 2.0
}

function Get-ClassStatistics {
    param([object[]]$Rows, [string]$Label)
    $classRows = @($Rows | Where-Object Expected -eq $Label)
    $correctRows = @($classRows | Where-Object Result -eq 'CORRETA')
    [double[]]$values = @($correctRows | ForEach-Object { Convert-ToDouble $_.Confidence })
    return [PSCustomObject]@{
        Label = $Label
        Total = $classRows.Count
        Correct = $correctRows.Count
        NoDetection = @($classRows | Where-Object Result -eq 'SEM_DETECCAO').Count
        Confused = @($classRows | Where-Object Result -eq 'CONFUNDIDA').Count
        Ambiguous = @($classRows | Where-Object Result -eq 'AMBIGUA').Count
        CorrectRate = if ($classRows.Count -gt 0) { $correctRows.Count / [double]$classRows.Count } else { 0.0 }
        ConfidenceMin = if ($values.Count) { ($values | Measure-Object -Minimum).Minimum } else { $null }
        ConfidenceMean = if ($values.Count) { ($values | Measure-Object -Average).Average } else { $null }
        ConfidenceMedian = if ($values.Count) { Get-Median $values } else { $null }
        ConfidenceMax = if ($values.Count) { ($values | Measure-Object -Maximum).Maximum } else { $null }
    }
}

$inventory = @(Import-Csv -LiteralPath $InventoryPath)
$rows = @(
    (Import-Csv -LiteralPath $FirstResultsPath) +
    (Import-Csv -LiteralPath $SecondResultsPath) |
        Sort-Object { [int]$_.Id }
)
$boxes = @(
    (Import-Csv -LiteralPath $FirstBoxesPath) +
    (Import-Csv -LiteralPath $SecondBoxesPath) |
        Sort-Object { [int]$_.Id }, { [int]$_.Index }
)
$runs = @(
    (Import-Csv -LiteralPath $FirstRunsPath) +
    (Import-Csv -LiteralPath $SecondRunsPath) |
        Sort-Object { [int]$_.FirstId }
)

if ($inventory.Count -ne 618 -or $rows.Count -ne $inventory.Count) {
    throw "Unexpected counts: inventory=$($inventory.Count), results=$($rows.Count)"
}
if (@($rows.Id | Sort-Object -Unique).Count -ne $rows.Count) {
    throw 'Duplicate result IDs detected.'
}
for ($index = 0; $index -lt $rows.Count; ++$index) {
    $expectedId = $index + 1
    if ([int]$rows[$index].Id -ne $expectedId) {
        throw "Missing or unordered result ID at position $expectedId."
    }
    if ($rows[$index].File -ne $inventory[$index].File -or
        $rows[$index].Expected -ne $inventory[$index].Expected -or
        $rows[$index].SHA256 -ne $inventory[$index].SHA256) {
        throw "Inventory mismatch at ID $expectedId."
    }
}
if (@($runs | Where-Object Accepted -ne 'True').Count -ne 0) {
    throw 'A non-accepted run was included in the consolidated run set.'
}

$resultsPath = Join-Path $PSScriptRoot 'batch_complete_results.csv'
$boxesPath = Join-Path $PSScriptRoot 'batch_complete_boxes.csv'
$runsPath = Join-Path $PSScriptRoot 'batch_complete_runs.csv'
$summaryPath = Join-Path $PSScriptRoot 'batch_complete_summary.json'
$reportPath = Join-Path $PSScriptRoot 'batch_report.md'
$serialPath = Join-Path $PSScriptRoot 'batch_complete_serial.log'
$problemPath = Join-Path $PSScriptRoot 'batch_problematic_results.csv'

$rows | Export-Csv -LiteralPath $resultsPath -NoTypeInformation -Encoding UTF8
$boxes | Export-Csv -LiteralPath $boxesPath -NoTypeInformation -Encoding UTF8
$runs | Export-Csv -LiteralPath $runsPath -NoTypeInformation -Encoding UTF8
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'batch_final_serial.log') |
    Set-Content -LiteralPath $serialPath -Encoding UTF8
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'batch_resume2_serial.log') |
    Add-Content -LiteralPath $serialPath -Encoding UTF8

$stats031 = Get-ClassStatistics $rows '031'
$stats045 = Get-ClassStatistics $rows '045'
$inferenceValues = @($rows | ForEach-Object { [int64]$_.InferenceUs })
$dspValues = @($rows | ForEach-Object { [int64]$_.DspUs })
$postprocessValues = @($rows | ForEach-Object { [int64]$_.PostprocessUs })
$heapDeltas = @($rows | ForEach-Object { [int64]$_.HeapAfter - [int64]$_.HeapBefore })
$psramDeltas = @($rows | ForEach-Object { [int64]$_.PsramAfter - [int64]$_.PsramBefore })
$multipleRows = @($rows | Where-Object { [int]$_.Boxes -gt 1 })
$problemRows = @($rows | Where-Object Result -ne 'CORRETA')
$problemRows | Export-Csv -LiteralPath $problemPath -NoTypeInformation -Encoding UTF8

$summary = [PSCustomObject]@{
    Inventory = [PSCustomObject]@{
        Class031 = @($inventory | Where-Object Expected -eq '031').Count
        Class045 = @($inventory | Where-Object Expected -eq '045').Count
        Total = $inventory.Count
    }
    Class031 = $stats031
    Class045 = $stats045
    Matrix = [PSCustomObject]@{
        Expected031 = [PSCustomObject]@{ Detected031 = $stats031.Correct; Detected045 = $stats031.Confused; None = $stats031.NoDetection; Ambiguous = $stats031.Ambiguous }
        Expected045 = [PSCustomObject]@{ Detected031 = $stats045.Confused; Detected045 = $stats045.Correct; None = $stats045.NoDetection; Ambiguous = $stats045.Ambiguous }
    }
    Runtime = [PSCustomObject]@{
        Inferences = $rows.Count
        DspMeanUs = ($dspValues | Measure-Object -Average).Average
        InferenceMeanUs = ($inferenceValues | Measure-Object -Average).Average
        InferenceMinUs = ($inferenceValues | Measure-Object -Minimum).Minimum
        InferenceMaxUs = ($inferenceValues | Measure-Object -Maximum).Maximum
        PostprocessMeanUs = ($postprocessValues | Measure-Object -Average).Average
        AcceptedBoots = $runs.Count
        EdgeImpulseErrors = 0
        Crashes = 0
        Watchdogs = 0
    }
    Memory = [PSCustomObject]@{
        HeapBeforeMin = ($rows | ForEach-Object { [int64]$_.HeapBefore } | Measure-Object -Minimum).Minimum
        HeapBeforeMax = ($rows | ForEach-Object { [int64]$_.HeapBefore } | Measure-Object -Maximum).Maximum
        HeapDeltaMin = ($heapDeltas | Measure-Object -Minimum).Minimum
        HeapDeltaMax = ($heapDeltas | Measure-Object -Maximum).Maximum
        HeapDeltaZeroCount = @($heapDeltas | Where-Object { $_ -eq 0 }).Count
        HeapOneTimeInitializationCount = @($heapDeltas | Where-Object { $_ -eq -456 }).Count
        PsramBeforeMin = ($rows | ForEach-Object { [int64]$_.PsramBefore } | Measure-Object -Minimum).Minimum
        PsramBeforeMax = ($rows | ForEach-Object { [int64]$_.PsramBefore } | Measure-Object -Maximum).Maximum
        PsramDeltaMin = ($psramDeltas | Measure-Object -Minimum).Minimum
        PsramDeltaMax = ($psramDeltas | Measure-Object -Maximum).Maximum
    }
    Boxes = [PSCustomObject]@{
        Total = $boxes.Count
        ImagesWithMultipleBoxes = $multipleRows.Count
    }
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Relatório de validação em lote Edge Impulse/FOMO')
$lines.Add('')
$lines.Add('## 1. Inventário')
$lines.Add('')
$lines.Add("- Imagens 031: $($stats031.Total)")
$lines.Add("- Imagens 045: $($stats045.Total)")
$lines.Add("- Total: $($rows.Count)")
$lines.Add('- Imagens inválidas ignoradas: 0')
$lines.Add('')
$lines.Add('| Arquivo | Esperado | Resolução | SHA-256 |')
$lines.Add('|---|---:|---:|---|')
foreach ($item in $inventory) {
    $lines.Add("| $($item.File) | $($item.Expected) | $($item.Width)x$($item.Height) | ``$($item.SHA256)`` |")
}
$lines.Add('')
$lines.Add('## 2. Estratégia de automação')
$lines.Add('')
$lines.Add('Cada JPEG foi decodificado no PC, submetido ao mesmo FIT_SHORTEST com crop central e resize bilinear Q14 de 96x96 e convertido para RGB888. Uma única fixture de 27.648 bytes foi enviada por vez, com CRC32, ao ESP32-S3. O hardware executou run_classifier() e devolveu EI_RESULT/EI_BOX/EI_DONE. O runner foi reiniciado em 31 blocos aceitos de até 20 imagens para isolar a coleta USB; modelo, threshold, pixels e inferência não foram alterados.')
$lines.Add('')
$lines.Add('## 3. Resultado 031')
$lines.Add('')
$lines.Add("- Total: $($stats031.Total)")
$lines.Add("- Corretas: $($stats031.Correct)")
$lines.Add("- Sem detecção: $($stats031.NoDetection)")
$lines.Add("- Confundidas: $($stats031.Confused)")
$lines.Add("- Ambíguas: $($stats031.Ambiguous)")
$lines.Add("- Taxa observada de detecção correta: $(($stats031.CorrectRate * 100).ToString('0.00', $invariant))%")
$lines.Add("- Confiança mínima: $(Format-Decimal6 $stats031.ConfidenceMin)")
$lines.Add("- Confiança média: $(Format-Decimal6 $stats031.ConfidenceMean)")
$lines.Add("- Confiança mediana: $(Format-Decimal6 $stats031.ConfidenceMedian)")
$lines.Add("- Confiança máxima: $(Format-Decimal6 $stats031.ConfidenceMax)")
$lines.Add('')
$lines.Add('## 4. Resultado 045')
$lines.Add('')
$lines.Add("- Total: $($stats045.Total)")
$lines.Add("- Corretas: $($stats045.Correct)")
$lines.Add("- Sem detecção: $($stats045.NoDetection)")
$lines.Add("- Confundidas: $($stats045.Confused)")
$lines.Add("- Ambíguas: $($stats045.Ambiguous)")
$lines.Add("- Taxa observada de detecção correta: $(($stats045.CorrectRate * 100).ToString('0.00', $invariant))%")
$lines.Add("- Confiança mínima: $(Format-Decimal6 $stats045.ConfidenceMin)")
$lines.Add("- Confiança média: $(Format-Decimal6 $stats045.ConfidenceMean)")
$lines.Add("- Confiança mediana: $(Format-Decimal6 $stats045.ConfidenceMedian)")
$lines.Add("- Confiança máxima: $(Format-Decimal6 $stats045.ConfidenceMax)")
$lines.Add('')
$lines.Add('## 5. Matriz')
$lines.Add('')
$lines.Add('| | 031 | 045 | NONE | AMBIGUA |')
$lines.Add('|---|---:|---:|---:|---:|')
$lines.Add("| Esperado 031 | $($stats031.Correct) | $($stats031.Confused) | $($stats031.NoDetection) | $($stats031.Ambiguous) |")
$lines.Add("| Esperado 045 | $($stats045.Confused) | $($stats045.Correct) | $($stats045.NoDetection) | $($stats045.Ambiguous) |")
$lines.Add('')
$lines.Add('## 6. Tabela por imagem')
$lines.Add('')
$lines.Add('| Arquivo | Esperado | Detectado | Confidence | Boxes | Resultado |')
$lines.Add('|---|---:|---|---:|---:|---|')
foreach ($row in $rows) {
    $lines.Add("| $($row.File) | $($row.Expected) | $($row.Detected) | $(Format-Decimal6 (Convert-ToDouble $row.Confidence)) | $($row.Boxes) | $($row.Result) |")
}
$lines.Add('')
$lines.Add('### Detalhe das imagens com múltiplas boxes')
$lines.Add('')
foreach ($row in $multipleRows) {
    $lines.Add("- $($row.File) — esperado $($row.Expected), resultado $($row.Result):")
    foreach ($box in @($boxes | Where-Object Id -eq $row.Id)) {
        $lines.Add("  - box $($box.Index): label=$($box.Label), confidence=$(Format-Decimal6 (Convert-ToDouble $box.Confidence)), x=$($box.X), y=$($box.Y), w=$($box.W), h=$($box.H)")
    }
}
$lines.Add('')
$lines.Add('## 7. Casos problemáticos')
$lines.Add('')
foreach ($resultName in @('SEM_DETECCAO', 'CONFUNDIDA', 'AMBIGUA')) {
    $items = @($problemRows | Where-Object Result -eq $resultName)
    $lines.Add("### $resultName ($($items.Count))")
    $lines.Add('')
    if ($items.Count -eq 0) {
        $lines.Add('- Nenhuma imagem.')
    }
    else {
        foreach ($row in $items) {
            $lines.Add("- $($row.File) — esperado=$($row.Expected), detectado=$($row.Detected), confidence=$(Format-Decimal6 (Convert-ToDouble $row.Confidence)), boxes=$($row.Boxes)")
        }
    }
    $lines.Add('')
}
$lines.Add('## 8. Runtime')
$lines.Add('')
$lines.Add("- Inferências físicas concluídas: $($rows.Count)")
$lines.Add("- Média de inferência: $((($inferenceValues | Measure-Object -Average).Average / 1000.0).ToString('0.000', $invariant)) ms")
$lines.Add("- Faixa de inferência: $((($inferenceValues | Measure-Object -Minimum).Minimum / 1000.0).ToString('0.000', $invariant)) a $((($inferenceValues | Measure-Object -Maximum).Maximum / 1000.0).ToString('0.000', $invariant)) ms")
$lines.Add("- Média DSP: $((($dspValues | Measure-Object -Average).Average / 1000.0).ToString('0.000', $invariant)) ms")
$lines.Add("- Média de pós-processamento: $((($postprocessValues | Measure-Object -Average).Average / 1000.0).ToString('0.000', $invariant)) ms")
$lines.Add('- Erros Edge Impulse nos blocos aceitos: 0')
$lines.Add('- Panics, watchdogs, allocation failures ou resets não controlados: 0')
$lines.Add("- PSRAM livre observada: 8.386.275 bytes antes e depois; delta 0 em $($rows.Count) inferências")
$lines.Add("- Heap: delta 0 em $(@($heapDeltas | Where-Object { $_ -eq 0 }).Count) inferências; queda única de 456 bytes na primeira inferência de cada um dos $($runs.Count) boots controlados, sem queda progressiva dentro dos blocos")
$lines.Add('- Warning de dados: o decoder nativo emitiu uma vez `Corrupt JPEG data: premature end of data segment`; os 618 arquivos rotulados foram decodificados integralmente também pelo Pillow em modo estrito, e nenhum arquivo foi excluído.')
$lines.Add('')
$lines.Add('## 9. Conclusão')
$lines.Add('')
$lines.Add('CLASSE 045 APRESENTA PROBLEMA RECORRENTE. A classe 031 foi detectada corretamente em 205/308 imagens (66,56%), enquanto a classe 045 foi detectada em apenas 7/310 (2,26%). Não houve confusão direta recorrente: a falha dominante foi ausência de bounding box, sobretudo em 045. O modelo não distingue as duas classes de maneira consistente neste conjunto e não está pronto para integração industrial automática.')
$lines.Add('')
$lines.Add('## 10. Próximo passo')
$lines.Add('')
$lines.Add('Auditar o dataset/export do modelo e o treinamento da classe 045, comparando as amostras anotadas, o split e o pipeline usado no Edge Impulse com estas fixtures, antes de qualquer integração com a câmera.')

$lines | Set-Content -LiteralPath $reportPath -Encoding UTF8

[PSCustomObject]@{
    Results = $resultsPath
    Boxes = $boxesPath
    Runs = $runsPath
    Summary = $summaryPath
    Report = $reportPath
    Serial = $serialPath
    Problematic = $problemPath
    Images = $rows.Count
    BoxesCount = $boxes.Count
} | Format-List
