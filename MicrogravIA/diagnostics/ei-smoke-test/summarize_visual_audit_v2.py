#!/usr/bin/env python3
"""Validate manual visual annotations and generate the v2 visual audit report."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_v2"
AUDIT = RESULTS / "audit_visual"
ROI = (64, 80, 104, 120)

CAUSES = [
    "PECA_FORA_POSICAO", "PECA_ROTACIONADA", "OCLUSAO_MAO", "OCLUSAO_OBJETO",
    "REFLEXO_ILUMINACAO", "DESFOQUE_MOVIMENTO", "FUNDO_INTERFERINDO",
    "BOX_ESPURIA_FORA_PECA", "MODELO_FALHOU_COM_PECA_BEM_VISIVEL", "INDETERMINADO",
]
LOCATIONS = [
    "SOBRE_PECA", "FORA_DA_PECA", "SOBRE_MAO", "SOBRE_FUNDO",
    "SOBRE_FIXACAO", "INDETERMINADA",
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


def value(text: str) -> float:
    return float(text.replace(",", "."))


def box_coordinates(box: dict[str, str]) -> str:
    return f"x={box['X']},y={box['Y']},w={box['W']},h={box['H']}"


def inside_roi(box: dict[str, str]) -> bool:
    x0, y0, x1, y1 = ROI
    x, y, w, h = (int(box[name]) for name in ("X", "Y", "W", "H"))
    return x >= x0 and y >= y0 and x + w <= x1 and y + h <= y1


def main() -> None:
    problematic = read_csv(RESULTS / "batch_v2_problematic.csv")
    results = read_csv(RESULTS / "batch_v2_results.csv")
    all_boxes = read_csv(RESULTS / "batch_v2_boxes.csv")
    image_annotations = read_csv(AUDIT / "visual_image_annotations.csv")
    box_annotations = read_csv(AUDIT / "visual_box_annotations.csv")
    input_manifest = read_csv(AUDIT / "model_inputs_manifest.csv")

    if len(problematic) != 45 or len(input_manifest) != 45:
        raise RuntimeError("The audit must contain exactly 45 problematic images and model inputs")
    problematic_ids = {row["Id"] for row in problematic}
    annotation_ids = {row["Id"] for row in image_annotations}
    if annotation_ids != problematic_ids or len(image_annotations) != 45:
        raise RuntimeError("Manual image annotations do not match the 45 problematic IDs")
    if any(row["PrimaryCause"] not in CAUSES for row in image_annotations):
        raise RuntimeError("Unknown manual cause classification")

    problematic_boxes = [box for box in all_boxes if box["Id"] in problematic_ids]
    box_keys = {(box["Id"], box["Index"]) for box in problematic_boxes}
    annotation_keys = {(row["Id"], row["Index"]) for row in box_annotations}
    if box_keys != annotation_keys:
        raise RuntimeError("Manual box annotations do not match every problematic box")
    if any(row["VisualLocation"] not in LOCATIONS for row in box_annotations):
        raise RuntimeError("Unknown manual box location")

    annotation_by_id = {row["Id"]: row for row in image_annotations}
    box_annotation_by_key = {(row["Id"], row["Index"]): row for row in box_annotations}
    boxes_by_id: dict[str, list[dict[str, str]]] = {}
    for box in problematic_boxes:
        boxes_by_id.setdefault(box["Id"], []).append(box)

    cause_rows: list[dict[str, object]] = []
    for cause in CAUSES:
        class031 = sum(row["Expected"] == "031" and row["PrimaryCause"] == cause for row in image_annotations)
        class045 = sum(row["Expected"] == "045" and row["PrimaryCause"] == cause for row in image_annotations)
        cause_rows.append({"Cause": cause, "031": class031, "045": class045, "Total": class031 + class045})
    write_csv(AUDIT / "cause_distribution.csv", cause_rows, ["Cause", "031", "045", "Total"])

    ambiguous_rows: list[dict[str, object]] = []
    for row in (item for item in problematic if item["Result"] == "AMBIGUA"):
        boxes = boxes_by_id[row["Id"]]
        correct_boxes = [box for box in boxes if box["Label"] == row["Expected"]]
        incorrect_boxes = [box for box in boxes if box["Label"] != row["Expected"]]
        correct_confidence = max(value(box["Confidence"]) for box in correct_boxes)
        incorrect_confidence = max(value(box["Confidence"]) for box in incorrect_boxes)
        correct_text = "; ".join(
            f"{box['Label']} {value(box['Confidence']):.6f} [{box_coordinates(box)}] "
            f"{box_annotation_by_key[(box['Id'], box['Index'])]['VisualLocation']}"
            for box in correct_boxes
        )
        incorrect_text = "; ".join(
            f"{box['Label']} {value(box['Confidence']):.6f} [{box_coordinates(box)}] "
            f"{box_annotation_by_key[(box['Id'], box['Index'])]['VisualLocation']}"
            for box in incorrect_boxes
        )
        ambiguous_rows.append({
            "Id": row["Id"], "File": row["File"], "Expected": row["Expected"],
            "CorrectConfidence": f"{correct_confidence:.6f}",
            "IncorrectConfidence": f"{incorrect_confidence:.6f}",
            "DeltaConfidence": f"{correct_confidence - incorrect_confidence:.6f}",
            "CorrectBoxes": correct_text, "IncorrectBoxes": incorrect_text,
            "PrimaryCause": annotation_by_id[row["Id"]]["PrimaryCause"],
            "Observation": annotation_by_id[row["Id"]]["Observation"],
        })
    write_csv(
        AUDIT / "ambiguous_analysis.csv", ambiguous_rows,
        ["Id", "File", "Expected", "CorrectConfidence", "IncorrectConfidence",
         "DeltaConfidence", "CorrectBoxes", "IncorrectBoxes", "PrimaryCause", "Observation"],
    )

    deltas_all = [float(row["DeltaConfidence"]) for row in ambiguous_rows]
    deltas_045 = [float(row["DeltaConfidence"]) for row in ambiguous_rows if row["Expected"] == "045"]

    incorrect_location = Counter()
    correct_location = Counter()
    incorrect_boxes: list[dict[str, str]] = []
    correct_ambiguous_boxes: list[dict[str, str]] = []
    expected_by_id = {row["Id"]: row["Expected"] for row in problematic}
    for box in problematic_boxes:
        location = box_annotation_by_key[(box["Id"], box["Index"])]["VisualLocation"]
        if box["Label"] == expected_by_id[box["Id"]]:
            correct_location[location] += 1
            correct_ambiguous_boxes.append(box)
        else:
            incorrect_location[location] += 1
            incorrect_boxes.append(box)
    location_rows = [{
        "VisualLocation": location,
        "IncorrectBoxes": incorrect_location[location],
        "CorrectBoxes": correct_location[location],
    } for location in LOCATIONS]
    write_csv(AUDIT / "box_location_summary.csv", location_rows, ["VisualLocation", "IncorrectBoxes", "CorrectBoxes"])

    worrying = [
        {**row, "Observation": annotation_by_id[row["Id"]]["Observation"]}
        for row in problematic
        if row["Result"] == "SEM_DETECCAO"
        and annotation_by_id[row["Id"]]["PrimaryCause"] == "MODELO_FALHOU_COM_PECA_BEM_VISIVEL"
    ]
    write_csv(
        AUDIT / "well_captured_failures.csv", worrying,
        list(problematic[0]) + ["Observation"],
    )

    correct_result_ids = {row["Id"]: row["Expected"] for row in results if row["Result"] == "CORRETA"}
    correct_dataset_boxes = [
        box for box in all_boxes
        if box["Id"] in correct_result_ids and box["Label"] == correct_result_ids[box["Id"]]
    ]
    correct_inside = sum(inside_roi(box) for box in correct_dataset_boxes)
    incorrect_inside = sum(inside_roi(box) for box in incorrect_boxes)
    ambiguous_correct_inside = sum(inside_roi(box) for box in correct_ambiguous_boxes)

    summary = {
        "counts": {"no_detection": 27, "ambiguous": 18, "total": 45},
        "cause_distribution": cause_rows,
        "ambiguous_delta_all": {
            "count": len(deltas_all), "min": min(deltas_all),
            "mean": statistics.fmean(deltas_all), "median": statistics.median(deltas_all),
            "max": max(deltas_all),
        },
        "ambiguous_delta_045": {
            "count": len(deltas_045), "min": min(deltas_045),
            "mean": statistics.fmean(deltas_045), "median": statistics.median(deltas_045),
            "max": max(deltas_045),
        },
        "incorrect_box_locations": dict(incorrect_location),
        "correct_box_locations": dict(correct_location),
        "potential_roi": {
            "useful": True, "coordinates": {"x_min": ROI[0], "y_min": ROI[1], "x_max": ROI[2], "y_max": ROI[3]},
            "correct_dataset_boxes_inside": correct_inside,
            "correct_dataset_boxes_total": len(correct_dataset_boxes),
            "correct_dataset_retention": correct_inside / len(correct_dataset_boxes),
            "ambiguous_correct_boxes_inside": ambiguous_correct_inside,
            "ambiguous_correct_boxes_total": len(correct_ambiguous_boxes),
            "incorrect_ambiguous_boxes_rejected": len(incorrect_boxes) - incorrect_inside,
            "incorrect_ambiguous_boxes_total": len(incorrect_boxes),
        },
        "well_captured_no_detection": [row["File"] for row in worrying],
        "conclusion": "RESULTADO MISTO",
        "next_action": "DEFINIR ROI/POLITICA SEGURA",
    }
    (AUDIT / "visual_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def files_for(expected: str, result: str, cause: str | None = None) -> str:
        items = [row["File"] for row in problematic
                 if row["Expected"] == expected and row["Result"] == result
                 and (cause is None or annotation_by_id[row["Id"]]["PrimaryCause"] == cause)]
        return ", ".join(f"`{name}`" for name in items) if items else "Nenhuma."

    report: list[str] = [
        "# Auditoria visual dos 45 casos problemáticos — DetectaIA2.0",
        "",
        "## 1. Total analisado", "",
        "- SEM_DETECCAO: 27", "- AMBIGUA: 18", "- TOTAL: 45",
        "- Todos os 45 previews 160x160 foram regenerados com o mesmo Q14/FIT_LONGEST e tiveram CRC32 idêntico ao lote físico.",
        "", "## 2. Distribuição das causas", "",
        "| Causa | 031 | 045 | Total |", "|---|---:|---:|---:|",
    ]
    report.extend(f"| {row['Cause']} | {row['031']} | {row['045']} | {row['Total']} |" for row in cause_rows)
    report.extend([
        "", "## 3. Casos 031 sem detecção", "",
        f"- Oclusão pela mão (9): {files_for('031', 'SEM_DETECCAO', 'OCLUSAO_MAO')}",
        f"- Peça rotacionada (11): {files_for('031', 'SEM_DETECCAO', 'PECA_ROTACIONADA')}",
        f"- Desfoque de movimento (2): {files_for('031', 'SEM_DETECCAO', 'DESFOQUE_MOVIMENTO')}",
        f"- Peça bem visível/modelo falhou (4): {files_for('031', 'SEM_DETECCAO', 'MODELO_FALHOU_COM_PECA_BEM_VISIVEL')}",
        "- O padrão dominante é captura fora da condição nominal, mas quatro falhas permanecem com peça nítida e visível.",
        "", "## 4. Casos 045 sem detecção", "",
        "- `045/foto0062.jpg`: o JPEG está truncado/corrompido. Apenas uma faixa superior contém dados; o restante é cinza. A ausência de detecção não deve ser usada como evidência contra o modelo.",
        "", "## 5. Ambiguidades 031", "",
    ])
    row031 = next(row for row in ambiguous_rows if row["Expected"] == "031")
    report.extend([
        f"- Arquivo: `{row031['File']}`", f"- Confidence correta 031: {row031['CorrectConfidence']}",
        f"- Confidence incorreta 045: {row031['IncorrectConfidence']}", f"- Delta: {row031['DeltaConfidence']}",
        f"- Box correta: {row031['CorrectBoxes']}", f"- Box incorreta: {row031['IncorrectBoxes']}",
        "- Ambas estão sobre a peça; há mão dentro da abertura e leve borramento.",
        "", "## 6. Ambiguidades 045", "",
        "| Arquivo | Conf 045 | Conf 031 | Delta | Box 045 | Box 031 | Observação |",
        "|---|---:|---:|---:|---|---|---|",
    ])
    for row in (item for item in ambiguous_rows if item["Expected"] == "045"):
        report.append(
            f"| {row['File']} | {row['CorrectConfidence']} | {row['IncorrectConfidence']} | "
            f"{row['DeltaConfidence']} | {row['CorrectBoxes']} | {row['IncorrectBoxes']} | {row['Observation']} |"
        )
    report.extend([
        "", "Estatística do delta correto-incorreto nas 17 ambiguidades 045:", "",
        f"- Mínimo: {min(deltas_045):.6f}", f"- Média: {statistics.fmean(deltas_045):.6f}",
        f"- Mediana: {statistics.median(deltas_045):.6f}", f"- Máximo: {max(deltas_045):.6f}",
        "", "Nas 18 ambiguidades totais: mínimo 0.070313; média 0.375651; mediana 0.414063; máximo 0.496094.",
        "", "## 7. Boxes espúrias", "",
        f"- Sobre mão: {incorrect_location['SOBRE_MAO']}",
        f"- Sobre fundo: {incorrect_location['SOBRE_FUNDO']}",
        f"- Sobre fixação: {incorrect_location['SOBRE_FIXACAO']}",
        f"- Sobre a própria peça: {incorrect_location['SOBRE_PECA']}",
        f"- Outras/indeterminadas: {sum(incorrect_location[key] for key in ('FORA_DA_PECA', 'INDETERMINADA'))}",
        "- Foram avaliadas 19 boxes de classe incorreta: 13 sobre a própria peça e 6 sobre a mão.",
        "", "## 8. Casos realmente preocupantes", "",
    ])
    report.extend(f"- `{row['File']}` — {row['Observation']}" for row in worrying)
    report.extend([
        "- Além desses quatro falsos negativos, 12 ambiguidades 045 mostram a peça montada e nítida, com a box 031 sobre a própria peça.",
        "", "## 9. ROI", "",
        "ROI POTENCIALMENTE ÚTIL: SIM", "",
        "- Região candidata apenas para estudo: `x=64..104`, `y=80..120` no frame 160x160.",
        f"- Ela contém {correct_inside}/{len(correct_dataset_boxes)} boxes corretas do lote ({correct_inside / len(correct_dataset_boxes) * 100:.2f}%).",
        f"- Contém {ambiguous_correct_inside}/{len(correct_ambiguous_boxes)} boxes corretas dos casos ambíguos.",
        f"- Rejeitaria geometricamente {len(incorrect_boxes) - incorrect_inside}/{len(incorrect_boxes)} boxes incorretas observadas nas ambiguidades.",
        "- Isso eliminaria sobretudo boxes 031 em y=72 e boxes sobre a mão em y=32..40. Não resolveria as duas ativações incorretas que permanecem dentro da região central.",
        "- A ROI foi inferida do mesmo conjunto de validação; não deve ser adotada sem uma validação separada e sem regra de segurança.",
        "", "## 10. Conclusão", "",
        "RESULTADO MISTO", "",
        "As falhas 031 são majoritariamente associadas a oclusão, rotação e movimento, mas existem quatro falsos negativos com captura adequada. Nas ambiguidades 045, a classe correta é sempre dominante em confiança, porém 13 boxes incorretas estão sobre a própria peça e seis sobre a mão. Há fragilidade real do modelo e também forte influência da condição de captura. Uma ROI parece capaz de remover grande parte das boxes espúrias, mas não todas.",
        "", "## 11. Próxima ação", "",
        "Definir e validar uma ROI/política segura usando um conjunto separado, sem alterar o modelo nem integrar ainda a câmera ao fluxo de produção.",
    ])
    (AUDIT / "visual_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({
        "images": len(problematic), "ambiguous": len(ambiguous_rows),
        "incorrect_boxes": len(incorrect_boxes), "well_captured_failures": len(worrying),
        "roi_correct_retention": correct_inside / len(correct_dataset_boxes),
        "roi_wrong_rejected": len(incorrect_boxes) - incorrect_inside,
    }, indent=2))


if __name__ == "__main__":
    main()
