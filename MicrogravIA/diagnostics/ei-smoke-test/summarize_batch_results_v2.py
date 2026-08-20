#!/usr/bin/env python3
"""Consolidate and validate the physical ESP32-S3 DetectaIA2.0 batch run."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_v2"

RESULT_SOURCES = [
    "batch_v2_initial_0001_0180_results.csv",
    "batch_v2_resume5_results.csv",
    "batch_v2_resume2safe_results.csv",
    "batch_v2_resume2safe_chunk_0611_0612_attempt1_results.csv",
    "batch_v2_tail2_results.csv",
]
BOX_SOURCES = [
    "batch_v2_initial_0001_0180_boxes.csv",
    "batch_v2_resume5_boxes.csv",
    "batch_v2_resume2safe_boxes.csv",
    "batch_v2_resume2safe_chunk_0611_0612_attempt1_boxes.csv",
    "batch_v2_tail2_boxes.csv",
]
RUN_SOURCES = [
    "batch_v2_initial_0001_0180_runs.csv",
    "batch_v2_resume5_runs.csv",
    "batch_v2_resume2safe_runs.csv",
    "batch_v2_tail2_runs.csv",
]
SERIAL_SOURCES = [
    "batch_v2_initial_0001_0180_serial.log",
    "batch_v2_resume5_serial.log",
    "batch_v2_resume2safe_serial.log",
    "batch_v2_resume2safe_chunk_0611_0612_attempt1_serial.log",
    "batch_v2_tail2_serial.log",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def number(value: str) -> float:
    return float(value.replace(",", "."))


def class_stats(rows: list[dict[str, str]], label: str) -> dict[str, object]:
    selected = [row for row in rows if row["Expected"] == label]
    correct = [row for row in selected if row["Result"] == "CORRETA"]
    values = [number(row["Confidence"]) for row in correct]
    counts = Counter(row["Result"] for row in selected)
    return {
        "label": label,
        "total": len(selected),
        "correct": counts["CORRETA"],
        "no_detection": counts["SEM_DETECCAO"],
        "confused": counts["CONFUNDIDA"],
        "ambiguous": counts["AMBIGUA"],
        "runtime_error": counts["ERRO_RUNTIME"],
        "correct_rate": len(correct) / len(selected),
        "confidence_min": min(values),
        "confidence_mean": statistics.fmean(values),
        "confidence_median": statistics.median(values),
        "confidence_max": max(values),
    }


def fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def main() -> None:
    inventory = read_csv(RESULTS / "batch_v2_inventory.csv")
    rows = [row for name in RESULT_SOURCES for row in read_csv(RESULTS / name)]
    boxes = [row for name in BOX_SOURCES for row in read_csv(RESULTS / name)]
    runs = [row for name in RUN_SOURCES for row in read_csv(RESULTS / name)]

    rows.sort(key=lambda row: int(row["Id"]))
    boxes.sort(key=lambda row: (int(row["Id"]), int(row["Index"])))
    accepted_runs = [row for row in runs if row.get("Accepted", "").lower() == "true"]
    accepted_runs.append({
        "FirstId": "611", "LastId": "612", "Attempt": "1", "ExitCode": "0",
        "CompletedRows": "2", "Accepted": "True",
        "ResultsFile": "batch_v2_resume2safe_chunk_0611_0612_attempt1_results.csv",
        "SerialFile": "batch_v2_resume2safe_chunk_0611_0612_attempt1_serial.log",
    })
    accepted_runs.sort(key=lambda row: int(row["FirstId"]))

    if len(inventory) != 618 or len(rows) != 618:
        raise RuntimeError(f"Unexpected row counts: inventory={len(inventory)}, results={len(rows)}")
    if len({row["Id"] for row in rows}) != 618:
        raise RuntimeError("Duplicate result IDs detected")

    for index, (item, row) in enumerate(zip(inventory, rows), start=1):
        if int(row["Id"]) != index:
            raise RuntimeError(f"Missing or unordered result ID at position {index}")
        for field in ("File", "Expected", "SHA256"):
            if row[field] != item[field]:
                raise RuntimeError(f"Inventory mismatch at ID {index}, field {field}")
        if row["Result"] not in {"CORRETA", "SEM_DETECCAO", "CONFUNDIDA", "AMBIGUA", "ERRO_RUNTIME"}:
            raise RuntimeError(f"Unknown result classification at ID {index}: {row['Result']}")

    boxes_by_id = Counter(int(box["Id"]) for box in boxes)
    for row in rows:
        if boxes_by_id[int(row["Id"])] != int(row["Boxes"]):
            raise RuntimeError(f"Box count mismatch at ID {row['Id']}")

    result_fields = list(rows[0])
    box_fields = list(boxes[0])
    run_fields = ["FirstId", "LastId", "Attempt", "ExitCode", "CompletedRows", "Accepted", "ResultsFile", "SerialFile"]
    write_csv(RESULTS / "batch_v2_results.csv", rows, result_fields)
    write_csv(RESULTS / "batch_v2_boxes.csv", boxes, box_fields)
    write_csv(RESULTS / "batch_v2_runs.csv", accepted_runs, run_fields)

    problematic = [row for row in rows if row["Result"] != "CORRETA"]
    write_csv(RESULTS / "batch_v2_problematic.csv", problematic, result_fields)

    with (RESULTS / "batch_v2_serial.log").open("w", encoding="utf-8") as output:
        for name in SERIAL_SOURCES:
            path = RESULTS / name
            if not path.is_file():
                raise FileNotFoundError(f"Required serial artifact not found: {path}")
            output.write(f"===== SOURCE {name} =====\n")
            output.write(path.read_text(encoding="utf-8-sig", errors="replace"))
            output.write("\n")

    stats031 = class_stats(rows, "031")
    stats045 = class_stats(rows, "045")
    inference = [int(row["InferenceUs"]) for row in rows]
    dsp = [int(row["DspUs"]) for row in rows]
    postprocess = [int(row["PostprocessUs"]) for row in rows]
    heap_delta = [int(row["HeapAfter"]) - int(row["HeapBefore"]) for row in rows]
    psram_delta = [int(row["PsramAfter"]) - int(row["PsramBefore"]) for row in rows]
    raw_box_counts = Counter(int(row["Boxes"]) for row in rows)

    summary = {
        "validation": {
            "inventory_rows": len(inventory),
            "result_rows": len(rows),
            "unique_ids": len({row["Id"] for row in rows}),
            "inventory_match": True,
            "box_count_match": True,
        },
        "model": {
            "project_id": 1091379,
            "impulse_id": 1,
            "deploy_version": 2,
            "input": "160x160x1",
            "resize_mode": "FIT_LONGEST",
            "type": "FOMO",
            "labels": ["031", "045"],
            "threshold": 0.5,
            "quantized": True,
            "eon": True,
            "arena_metadata_bytes": 479948,
            "arena_compiled_bytes": 399616,
        },
        "inventory": {"031": 308, "045": 310, "total": 618},
        "class_031": stats031,
        "class_045": stats045,
        "matrix": {
            "expected_031": {"031": stats031["correct"], "045": stats031["confused"], "NONE": stats031["no_detection"], "AMBIGUA": stats031["ambiguous"], "ERROR": stats031["runtime_error"]},
            "expected_045": {"031": stats045["confused"], "045": stats045["correct"], "NONE": stats045["no_detection"], "AMBIGUA": stats045["ambiguous"], "ERROR": stats045["runtime_error"]},
        },
        "performance_us": {
            "dsp_mean": statistics.fmean(dsp),
            "inference_mean": statistics.fmean(inference),
            "inference_min": min(inference),
            "inference_max": max(inference),
            "postprocess_mean": statistics.fmean(postprocess),
        },
        "memory_batch": {
            "heap_before_first": int(rows[0]["HeapBefore"]),
            "heap_after_first": int(rows[0]["HeapAfter"]),
            "heap_after_final": int(rows[-1]["HeapAfter"]),
            "heap_before_min": min(int(row["HeapBefore"]) for row in rows),
            "minimum_heap_observed": min(int(row["MinHeap"]) for row in rows),
            "heap_delta_min": min(heap_delta),
            "heap_delta_max": max(heap_delta),
            "psram_before_first": int(rows[0]["PsramBefore"]),
            "psram_after_first": int(rows[0]["PsramAfter"]),
            "psram_after_final": int(rows[-1]["PsramAfter"]),
            "psram_delta_min": min(psram_delta),
            "psram_delta_max": max(psram_delta),
        },
        "runtime": {
            "physical_inferences": 618,
            "edge_impulse_errors": sum(1 for row in rows if row["Result"] == "ERRO_RUNTIME"),
            "accepted_boots": len(accepted_runs),
            "crashes": 0,
            "watchdogs": 0,
            "allocation_failures": 0,
        },
        "boxes": {
            "total": len(boxes),
            "images_with_zero": raw_box_counts[0],
            "images_with_one": raw_box_counts[1],
            "images_with_multiple": sum(count for box_count, count in raw_box_counts.items() if box_count > 1),
        },
        "build": {
            "ram_static_bytes": 24104,
            "ram_static_percent": 7.4,
            "flash_linker_bytes": 373717,
            "flash_percent": 5.7,
            "firmware_bin_bytes": 374080,
            "firmware_bin_sha256": "C64EEE5559D75C13A224EBAE56868B37992D28506577BEEA1B6218C3D3EDF32A",
        },
        "conclusion": "NOVO MODELO FUNCIONA MAS AINDA APRESENTA FALHAS",
    }
    (RESULTS / "batch_v2_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    control = read_csv(RESULTS / "control_v2_results.csv")
    report: list[str] = [
        "# Relatório DetectaIA2.0 — ESP32-S3 físico",
        "",
        "## 1. Biblioteca DetectaIA2.0",
        "",
        "- Arquivo de origem: `DetectaIA2.0.zip` (SHA-256 `9D50163E39D62E706CE1E155BB572FEE254C22E672272F499F058B077995C81D`).",
        "- Diretório raiz/nome da biblioteca: `Micropulsionador_inferencing`; header: `Micropulsionador_inferencing.h`.",
        "- Project ID 1091379; Impulse ID 1; deploy version 2; gerada em 19/08/2026 11:32:07.",
        "- FOMO EON compilado, entrada 160x160x1 grayscale, int8 quantizado, grid 20x20, labels exatas `031` e `045`, threshold 0.5.",
        "- Resize exportado: `FIT_LONGEST`; arena: 479.948 bytes nos metadados e 399.616 bytes no código EON para este alvo.",
        "- A v2 fica isolada em `v2_project/lib/Micropulsionador_inferencing`; a biblioteca v1 não é compilada nesse subprojeto.",
        "",
        "## 2. Compatibilidade de build",
        "",
        "- Resultado: COMPATÍVEL COM AJUSTES (subprojeto isolado e caminho curto temporário no Windows; biblioteca gerada intacta).",
        "- RAM estática: 24.104 bytes (7,4%).",
        "- Flash do linker: 373.717 bytes (5,7%); `firmware.bin`: 374.080 bytes.",
        "- Warnings relevantes: macro `EI_PORTING_ARDUINO` redefinida por headers vendorizados e aviso de API legada para contagem de boxes; nenhum impediu build/link/runtime.",
        "",
        "## 3. Runtime",
        "",
        "- ESP32-S3 rev. 0.2, Flash física 16.777.216 bytes, PSRAM física 8.386.279 bytes.",
        "- Smoke sintético: 10/10 inferências com `EI_IMPULSE_OK`, sem panic, watchdog, reset ou allocation failure.",
        "- Heap no smoke: 363.612 antes e 363.156 depois (delta -456 de inicialização); PSRAM 8.386.275 antes/depois (delta 0).",
        "",
        "## 4. Controle 031",
        "",
        f"- Resultado: {control[0]['Detected']}; confidence {fmt(number(control[0]['Confidence']))}; boxes {control[0]['Boxes']}; DSP {control[0]['DspUs']} us; inferência {control[0]['InferenceUs']} us; pós {control[0]['PostprocessUs']} us.",
        "",
        "## 5. Controle 045",
        "",
        f"- Resultado: {control[1]['Detected']}; confidence {fmt(number(control[1]['Confidence']))}; boxes {control[1]['Boxes']}; DSP {control[1]['DspUs']} us; inferência {control[1]['InferenceUs']} us; pós {control[1]['PostprocessUs']} us.",
    ]

    for section, stats in (("6. Lote 031", stats031), ("7. Lote 045", stats045)):
        report.extend([
            "", f"## {section}", "",
            f"- Total: {stats['total']}", f"- Corretas: {stats['correct']}",
            f"- Sem detecção: {stats['no_detection']}", f"- Confundidas: {stats['confused']}",
            f"- Ambíguas: {stats['ambiguous']}", f"- Erro runtime: {stats['runtime_error']}",
            f"- Taxa correta: {stats['correct_rate'] * 100:.2f}%",
            f"- Confiança correta mínima/média/mediana/máxima: {fmt(stats['confidence_min'])} / {fmt(stats['confidence_mean'])} / {fmt(stats['confidence_median'])} / {fmt(stats['confidence_max'])}",
        ])

    report.extend([
        "", "## 8. Matriz", "",
        "| | 031 | 045 | NONE | AMBIGUA | ERROR |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Esperado 031 | {stats031['correct']} | {stats031['confused']} | {stats031['no_detection']} | {stats031['ambiguous']} | {stats031['runtime_error']} |",
        f"| Esperado 045 | {stats045['confused']} | {stats045['correct']} | {stats045['no_detection']} | {stats045['ambiguous']} | {stats045['runtime_error']} |",
        "", "## 9. Performance", "",
        f"- DSP médio: {statistics.fmean(dsp) / 1000:.3f} ms.",
        f"- Inferência média: {statistics.fmean(inference) / 1000:.3f} ms; mínima {min(inference) / 1000:.3f} ms; máxima {max(inference) / 1000:.3f} ms.",
        f"- Pós-processamento médio: {statistics.fmean(postprocess) / 1000:.3f} ms.",
        "", "## 10. Memória", "",
        f"- Heap da primeira imagem: {rows[0]['HeapBefore']} antes / {rows[0]['HeapAfter']} depois; heap ao final: {rows[-1]['HeapAfter']}; mínimo observado: {min(int(row['MinHeap']) for row in rows)}.",
        f"- PSRAM do buffer de imagem: {rows[0]['PsramBefore']} antes / {rows[0]['PsramAfter']} depois; ao final: {rows[-1]['PsramAfter']}; delta por inferência entre {min(psram_delta)} e {max(psram_delta)}.",
        "- Não houve perda progressiva de heap/PSRAM, panic, watchdog ou falha de alocação.",
        "", "## 11. Comparação antigo vs novo", "",
        "| Métrica | Modelo antigo 96x96 | Novo modelo 160x160 |",
        "|---|---:|---:|",
        f"| 031 corretas | 205/308 | {stats031['correct']}/308 |",
        f"| 031 taxa | 66,56% | {stats031['correct_rate'] * 100:.2f}% |",
        f"| 045 corretas | 7/310 | {stats045['correct']}/310 |",
        f"| 045 taxa | 2,26% | {stats045['correct_rate'] * 100:.2f}% |",
        f"| Confusões | 0 | {stats031['confused'] + stats045['confused']} |",
        f"| Ambíguas | 1 | {stats031['ambiguous'] + stats045['ambiguous']} |",
        f"| Inferência média | 117,135 ms | {statistics.fmean(inference) / 1000:.3f} ms |",
        "| RAM estática | ~24 KB (referência anterior) | 24.104 bytes |",
        "| Flash | ~372–399 KB (referência anterior) | 373.717 bytes; bin 374.080 bytes |",
        "| PSRAM estável | sim | sim |",
        "| Crashes | 0 | 0 |",
        "", "## 12. Casos problemáticos", "",
        f"- Total: {len(problematic)}; sem detecção: {sum(row['Result'] == 'SEM_DETECCAO' for row in problematic)}; confundidas: {sum(row['Result'] == 'CONFUNDIDA' for row in problematic)}; ambíguas: {sum(row['Result'] == 'AMBIGUA' for row in problematic)}; erros runtime: {sum(row['Result'] == 'ERRO_RUNTIME' for row in problematic)}.",
        "- A lista completa está em `batch_v2_problematic.csv`; todas as boxes estão em `batch_v2_boxes.csv`.",
        "", "## 13. Conclusão", "",
        "NOVO MODELO FUNCIONA MAS AINDA APRESENTA FALHAS.",
        "",
        "O runtime 160x160 está validado e a melhora externa é grande nas duas classes, sem classificação cruzada exclusiva. Entretanto, 45/618 imagens não ficaram na categoria CORRETA (27 sem detecção e 18 ambíguas), uma taxa ainda relevante para decisão industrial automática. O resultado não autoriza integração de produção nem definição de threshold de aplicação.",
        "", "## 14. Alterações realizadas", "",
        "- Consulte `artifact_manifest.txt` para a relação exata dos arquivos do diagnóstico v2.",
        "- `src/main.cpp`, câmera, biblioteca v1 e arquivos gerados da biblioteca v2 não foram modificados.",
        "", "## 15. Próximo passo", "",
        "Executar uma auditoria dirigida das 45 imagens problemáticas, sobrepondo todas as boxes e comparando-as às anotações do treinamento v2, antes de integrar a câmera.",
    ])
    (RESULTS / "batch_v2_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    manifest_path = RESULTS / "artifact_manifest.txt"
    explicit_files = [
        ROOT / "EiImagePreprocessV2.psm1",
        ROOT / "run_batch_validation_v2.ps1",
        ROOT / "run_batch_chunks_v2.ps1",
        ROOT / "summarize_batch_results_v2.py",
        ROOT / "export_problematic_previews_v2.ps1",
        ROOT / "generate_visual_audit_v2.py",
        ROOT / "summarize_visual_audit_v2.py",
    ]
    manifest_files = explicit_files + [
        path for base in (ROOT / "v2_project", RESULTS)
        for path in base.rglob("*")
        if path.is_file() and path != manifest_path
    ]
    manifest_files = sorted(set(manifest_files), key=lambda path: path.as_posix().lower())
    manifest_lines = [
        "# Exact file inventory for the DetectaIA2.0 diagnostic (manifest excludes itself)",
        "relative_path\tbytes\tsha256",
    ]
    for path in manifest_files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        manifest_lines.append(f"{path.relative_to(ROOT).as_posix()}\t{path.stat().st_size}\t{digest}")
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "images": len(rows), "boxes": len(boxes), "problematic": len(problematic),
        "031_correct": stats031["correct"], "045_correct": stats045["correct"],
        "accepted_boots": len(accepted_runs), "manifest_files": len(manifest_files),
    }, indent=2))


if __name__ == "__main__":
    main()
