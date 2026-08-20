#!/usr/bin/env python3
"""Retrospective fail-safe policy simulation over existing FOMO v2 results."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results_v2"
OUTPUT = RESULTS / "policy_simulation"
CORRUPTED_FILE = "045/foto0062.jpg"
ROI_BOUNDS = (64.0, 80.0, 104.0, 120.0)
CONFIDENCES = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95)
MARGINS = (0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
ROI_MODES = ("NONE", "ROI_CENTER", "ROI_INTERSECTION_50")
DECISIONS = (
    "ACCEPT_031", "ACCEPT_045", "REJECT_NO_DETECTION",
    "REJECT_LOW_CONFIDENCE", "REJECT_AMBIGUOUS",
)


@dataclass(frozen=True)
class Policy:
    roi: str
    confidence: float
    margin: float

    @property
    def policy_id(self) -> str:
        return f"{self.roi}_C{self.confidence:.2f}_M{self.margin:.2f}"


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


def score(text: str) -> float:
    return float(text.replace(",", "."))


def roi_accepts(box: dict[str, str], mode: str) -> tuple[bool, float]:
    if mode == "NONE":
        return True, 1.0
    x, y, w, h = (float(box[field]) for field in ("X", "Y", "W", "H"))
    x_min, y_min, x_max, y_max = ROI_BOUNDS
    if mode == "ROI_CENTER":
        center_x = x + w / 2.0
        center_y = y + h / 2.0
        accepted = x_min <= center_x <= x_max and y_min <= center_y <= y_max
        return accepted, 1.0 if accepted else 0.0
    if mode == "ROI_INTERSECTION_50":
        intersection_width = max(0.0, min(x + w, x_max) - max(x, x_min))
        intersection_height = max(0.0, min(y + h, y_max) - max(y, y_min))
        fraction = (intersection_width * intersection_height) / (w * h)
        return fraction >= 0.50, fraction
    raise ValueError(f"Unknown ROI mode: {mode}")


def decide(
    row: dict[str, str],
    boxes: list[dict[str, str]],
    policy: Policy,
) -> dict[str, object]:
    spatial: list[tuple[dict[str, str], float]] = []
    for box in boxes:
        accepted, fraction = roi_accepts(box, policy.roi)
        if accepted:
            spatial.append((box, fraction))

    if not spatial:
        return {
            "Decision": "REJECT_NO_DETECTION", "AcceptedLabel": "NONE",
            "Best031": "", "Best045": "", "Delta": "",
            "RawBoxes": len(boxes), "RoiBoxes": 0, "ConfidenceBoxes": 0,
        }

    confident = [(box, fraction) for box, fraction in spatial
                 if score(box["Confidence"]) >= policy.confidence]
    if not confident:
        return {
            "Decision": "REJECT_LOW_CONFIDENCE", "AcceptedLabel": "NONE",
            "Best031": "", "Best045": "", "Delta": "",
            "RawBoxes": len(boxes), "RoiBoxes": len(spatial), "ConfidenceBoxes": 0,
        }

    best: dict[str, float] = {}
    for box, _ in confident:
        best[box["Label"]] = max(best.get(box["Label"], 0.0), score(box["Confidence"]))
    best031 = best.get("031")
    best045 = best.get("045")
    common = {
        "Best031": "" if best031 is None else f"{best031:.6f}",
        "Best045": "" if best045 is None else f"{best045:.6f}",
        "RawBoxes": len(boxes), "RoiBoxes": len(spatial),
        "ConfidenceBoxes": len(confident),
    }

    if best031 is None:
        return {**common, "Decision": "ACCEPT_045", "AcceptedLabel": "045", "Delta": ""}
    if best045 is None:
        return {**common, "Decision": "ACCEPT_031", "AcceptedLabel": "031", "Delta": ""}

    delta = abs(best031 - best045)
    if best031 == best045 or delta < policy.margin:
        return {
            **common, "Decision": "REJECT_AMBIGUOUS", "AcceptedLabel": "NONE",
            "Delta": f"{delta:.6f}",
        }
    accepted = "031" if best031 > best045 else "045"
    return {
        **common, "Decision": f"ACCEPT_{accepted}", "AcceptedLabel": accepted,
        "Delta": f"{delta:.6f}",
    }


def metrics(decisions: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(str(row["Decision"]) for row in decisions)
    accepted = [row for row in decisions if str(row["Decision"]).startswith("ACCEPT_")]
    correct = sum(row["AcceptedLabel"] == row["Expected"] for row in accepted)
    wrong = len(accepted) - correct
    total = len(decisions)
    accepted_count = len(accepted)
    return {
        "TotalImages": total,
        "CorrectAccept": correct,
        "WrongAccept": wrong,
        "RejectNoDetection": counts["REJECT_NO_DETECTION"],
        "RejectLowConfidence": counts["REJECT_LOW_CONFIDENCE"],
        "RejectAmbiguous": counts["REJECT_AMBIGUOUS"],
        "Accepted": accepted_count,
        "TotalRejects": total - accepted_count,
        "Coverage": accepted_count / total if total else 0.0,
        "AcceptedAccuracy": correct / accepted_count if accepted_count else 0.0,
    }


def policy_metrics(
    policy: Policy,
    decisions: list[dict[str, object]],
) -> dict[str, object]:
    all_metrics = metrics(decisions)
    clean_metrics = metrics([row for row in decisions if row["File"] != CORRUPTED_FILE])
    amb045 = [row for row in decisions
              if row["Expected"] == "045" and row["RawResult"] == "AMBIGUA"]
    amb_counts = Counter(str(row["Decision"]) for row in amb045)
    row: dict[str, object] = {
        "PolicyId": policy.policy_id, "ROI": policy.roi,
        "MinConfidence": f"{policy.confidence:.2f}",
        "MinMargin": f"{policy.margin:.2f}",
        **all_metrics,
        "Coverage": f"{all_metrics['Coverage']:.9f}",
        "AcceptedAccuracy": f"{all_metrics['AcceptedAccuracy']:.9f}",
        "WithoutCorruptedTotal": clean_metrics["TotalImages"],
        "WithoutCorruptedCorrectAccept": clean_metrics["CorrectAccept"],
        "WithoutCorruptedWrongAccept": clean_metrics["WrongAccept"],
        "WithoutCorruptedNoDetection": clean_metrics["RejectNoDetection"],
        "WithoutCorruptedLowConfidence": clean_metrics["RejectLowConfidence"],
        "WithoutCorruptedAmbiguous": clean_metrics["RejectAmbiguous"],
        "WithoutCorruptedCoverage": f"{clean_metrics['Coverage']:.9f}",
        "WithoutCorruptedAcceptedAccuracy": f"{clean_metrics['AcceptedAccuracy']:.9f}",
        "Amb045Accept045": amb_counts["ACCEPT_045"],
        "Amb045RejectNoDetection": amb_counts["REJECT_NO_DETECTION"],
        "Amb045RejectLowConfidence": amb_counts["REJECT_LOW_CONFIDENCE"],
        "Amb045RejectAmbiguous": amb_counts["REJECT_AMBIGUOUS"],
        "Amb045WrongAccept": amb_counts["ACCEPT_031"],
    }
    return row


def dominates(left: dict[str, object], right: dict[str, object]) -> bool:
    left_wrong, right_wrong = int(left["WrongAccept"]), int(right["WrongAccept"])
    left_acc, right_acc = float(left["AcceptedAccuracy"]), float(right["AcceptedAccuracy"])
    left_cov, right_cov = float(left["Coverage"]), float(right["Coverage"])
    no_worse = left_wrong <= right_wrong and left_acc >= right_acc and left_cov >= right_cov
    strictly_better = left_wrong < right_wrong or left_acc > right_acc or left_cov > right_cov
    return no_worse and strictly_better


def format_reference(row: dict[str, object]) -> str:
    return (
        f"Correct={row['CorrectAccept']}, Wrong={row['WrongAccept']}, "
        f"NoDetection={row['RejectNoDetection']}, LowConfidence={row['RejectLowConfidence']}, "
        f"Ambiguous={row['RejectAmbiguous']}, Coverage={float(row['Coverage']) * 100:.2f}%, "
        f"AcceptedAccuracy={float(row['AcceptedAccuracy']) * 100:.2f}%"
    )


def main() -> None:
    results = read_csv(RESULTS / "batch_v2_results.csv")
    boxes = read_csv(RESULTS / "batch_v2_boxes.csv")
    boxes_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for box in boxes:
        boxes_by_id[box["Id"]].append(box)

    baseline = {
        "031_correct": sum(row["Expected"] == "031" and row["Result"] == "CORRETA" for row in results),
        "045_correct": sum(row["Expected"] == "045" and row["Result"] == "CORRETA" for row in results),
        "no_detection": sum(row["Result"] == "SEM_DETECCAO" for row in results),
        "ambiguous": sum(row["Result"] == "AMBIGUA" for row in results),
    }
    expected_baseline = {"031_correct": 281, "045_correct": 292, "no_detection": 27, "ambiguous": 18}
    if len(results) != 618 or baseline != expected_baseline:
        raise RuntimeError(
            f"BASELINE INCONSISTENT: total={len(results)}, actual={baseline}, expected={expected_baseline}"
        )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    policies = [Policy(roi, confidence, margin)
                for roi in ROI_MODES for confidence in CONFIDENCES for margin in MARGINS]
    per_image: list[dict[str, object]] = []
    grid: list[dict[str, object]] = []
    decisions_by_policy: dict[str, list[dict[str, object]]] = {}

    for policy in policies:
        decisions: list[dict[str, object]] = []
        for row in results:
            decision = decide(row, boxes_by_id[row["Id"]], policy)
            accepted_label = str(decision["AcceptedLabel"])
            is_accept = str(decision["Decision"]).startswith("ACCEPT_")
            item: dict[str, object] = {
                "PolicyId": policy.policy_id, "ROI": policy.roi,
                "MinConfidence": f"{policy.confidence:.2f}",
                "MinMargin": f"{policy.margin:.2f}",
                "Id": row["Id"], "File": row["File"], "Expected": row["Expected"],
                "RawResult": row["Result"], "IsCorruptedImage": row["File"] == CORRUPTED_FILE,
                **decision,
                "IsCorrectAccept": is_accept and accepted_label == row["Expected"],
                "IsWrongAccept": is_accept and accepted_label != row["Expected"],
            }
            decisions.append(item)
            per_image.append(item)
        decisions_by_policy[policy.policy_id] = decisions
        grid.append(policy_metrics(policy, decisions))

    grid_fields = list(grid[0])
    write_csv(OUTPUT / "policy_grid.csv", grid, grid_fields)
    write_csv(OUTPUT / "policy_per_image.csv", per_image, list(per_image[0]))

    without_corrupted: list[dict[str, object]] = []
    for row in grid:
        without_corrupted.append({
            "PolicyId": row["PolicyId"], "ROI": row["ROI"],
            "MinConfidence": row["MinConfidence"], "MinMargin": row["MinMargin"],
            "TotalImages": row["WithoutCorruptedTotal"],
            "CorrectAccept": row["WithoutCorruptedCorrectAccept"],
            "WrongAccept": row["WithoutCorruptedWrongAccept"],
            "RejectNoDetection": row["WithoutCorruptedNoDetection"],
            "RejectLowConfidence": row["WithoutCorruptedLowConfidence"],
            "RejectAmbiguous": row["WithoutCorruptedAmbiguous"],
            "Coverage": row["WithoutCorruptedCoverage"],
            "AcceptedAccuracy": row["WithoutCorruptedAcceptedAccuracy"],
        })
    write_csv(OUTPUT / "policy_grid_without_corrupted.csv", without_corrupted, list(without_corrupted[0]))

    sorted_grid = sorted(
        grid,
        key=lambda row: (
            int(row["WrongAccept"]), -float(row["AcceptedAccuracy"]),
            -float(row["Coverage"]), int(row["TotalRejects"]),
            str(row["ROI"]), float(row["MinConfidence"]), float(row["MinMargin"]),
        ),
    )
    top15 = sorted_grid[:15]
    write_csv(OUTPUT / "policy_top15.csv", top15, grid_fields)

    pareto = [candidate for candidate in grid
              if not any(dominates(other, candidate) for other in grid if other is not candidate)]
    pareto.sort(key=lambda row: (
        int(row["WrongAccept"]), -float(row["AcceptedAccuracy"]),
        -float(row["Coverage"]), str(row["ROI"]),
        float(row["MinConfidence"]), float(row["MinMargin"]),
    ))
    write_csv(OUTPUT / "policy_pareto.csv", pareto, grid_fields)

    references = {
        "A": "NONE_C0.50_M0.00",
        "B": "ROI_CENTER_C0.50_M0.00",
        "C": "ROI_CENTER_C0.90_M0.00",
        "D": "ROI_CENTER_C0.90_M0.10",
        "E": "ROI_CENTER_C0.95_M0.15",
    }
    grid_by_id = {str(row["PolicyId"]): row for row in grid}
    reference_rows: list[dict[str, object]] = []
    for name, policy_id in references.items():
        reference_rows.append({"Scenario": name, **grid_by_id[policy_id]})
    write_csv(OUTPUT / "policy_references.csv", reference_rows, ["Scenario"] + grid_fields)

    amb045_reference: list[dict[str, object]] = []
    for name, policy_id in references.items():
        row = grid_by_id[policy_id]
        amb045_reference.append({
            "Scenario": name, "PolicyId": policy_id,
            "Accept045": row["Amb045Accept045"],
            "RejectNoDetection": row["Amb045RejectNoDetection"],
            "RejectLowConfidence": row["Amb045RejectLowConfidence"],
            "RejectAmbiguous": row["Amb045RejectAmbiguous"],
            "WrongAccept": row["Amb045WrongAccept"],
        })
    write_csv(
        OUTPUT / "policy_ambiguities_045.csv", amb045_reference,
        ["Scenario", "PolicyId", "Accept045", "RejectNoDetection",
         "RejectLowConfidence", "RejectAmbiguous", "WrongAccept"],
    )

    ambiguity031_rows: list[dict[str, object]] = []
    for confidence in CONFIDENCES:
        for margin in MARGINS:
            policy_id = Policy("NONE", confidence, margin).policy_id
            decision = next(row for row in decisions_by_policy[policy_id]
                            if row["File"] == "031/foto0263.jpg")
            ambiguity031_rows.append({
                "MinConfidence": f"{confidence:.2f}", "MinMargin": f"{margin:.2f}",
                "Decision": decision["Decision"], "Best031": decision["Best031"],
                "Best045": decision["Best045"], "Delta": decision["Delta"],
                "Note": "ROI_CENTER and ROI_INTERSECTION_50 give the same result; both boxes pass either ROI.",
            })
    write_csv(
        OUTPUT / "policy_ambiguity_031.csv", ambiguity031_rows,
        ["MinConfidence", "MinMargin", "Decision", "Best031", "Best045", "Delta", "Note"],
    )

    false_negative_files = {
        "031/foto0286.jpg", "031/foto0287.jpg", "031/foto0288.jpg", "031/foto0290.jpg"
    }
    false_negative_check = Counter()
    corrupted_check = Counter()
    for row in per_image:
        if row["File"] in false_negative_files:
            false_negative_check[str(row["Decision"])] += 1
        if row["File"] == CORRUPTED_FILE:
            corrupted_check[str(row["Decision"])] += 1
    if false_negative_check != Counter({"REJECT_NO_DETECTION": 147 * 4}):
        raise RuntimeError(f"Fail-safe violation in known false negatives: {false_negative_check}")
    if corrupted_check != Counter({"REJECT_NO_DETECTION": 147}):
        raise RuntimeError(f"Unexpected corrupted image decision: {corrupted_check}")

    summary = {
        "baseline_validation": {"total": len(results), **baseline, "matches_expected": True},
        "grid": {
            "roi_modes": list(ROI_MODES), "confidences": list(CONFIDENCES),
            "margins": list(MARGINS), "policies": len(grid),
            "per_image_decisions": len(per_image),
            "policies_with_wrong_accept": sum(int(row["WrongAccept"]) > 0 for row in grid),
        },
        "roi": {
            "bounds": {"x_min": 64, "x_max": 104, "y_min": 80, "y_max": 120},
            "center": "box center inside inclusive ROI bounds",
            "intersection_50": "intersection area / box area >= 0.50",
        },
        "references": {name: grid_by_id[policy_id] for name, policy_id in references.items()},
        "top15_policy_ids": [row["PolicyId"] for row in top15],
        "pareto_policy_ids": [row["PolicyId"] for row in pareto],
        "false_negative_check": dict(false_negative_check),
        "corrupted_image_check": dict(corrupted_check),
        "warning": (
            "Esses parâmetros foram avaliados no mesmo conjunto usado para derivar a ROI e analisar os erros. "
            "Portanto, não podem ser considerados calibrados para produção."
        ),
        "conclusion": "ROI TEM BENEFÍCIO LIMITADO",
        "next_action": "COLETAR CONJUNTO INDEPENDENTE PARA VALIDAR A POLÍTICA",
    }
    (OUTPUT / "policy_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report: list[str] = [
        "# Simulação retrospectiva de políticas — DetectaIA2.0", "",
        "## 1. Validação dos dados de entrada", "",
        "- 031 corretas: 281", "- 045 corretas: 292",
        "- Sem detecção: 27", "- Ambíguas: 18", "- Total: 618",
        "- O baseline reproduziu exatamente os números consolidados; a grade foi executada.",
        "", "## 2. Metodologia", "",
        "- ROI_CENTER: aceita a box quando seu centro está dentro de x=64..104 e y=80..120.",
        "- ROI_INTERSECTION_50: aceita quando pelo menos 50% da área da box intersecta a ROI.",
        "- O minimumVisionConfidence é aplicado somente depois da ROI e não altera o threshold FOMO interno 0.5.",
        "- Para cada classe permanece o maior score. Quando ambas permanecem, delta=abs(best031-best045); delta menor que a margem gera REJECT_AMBIGUOUS.",
        "- Ausência de box nunca é convertida em classificação. Box existente, mas removida integralmente pela ROI, resulta em REJECT_NO_DETECTION; remoção apenas pela confiança resulta em REJECT_LOW_CONFIDENCE.",
        "", "## 3. Baseline", "",
        "- Classificação bruta: 573 CORRETAS, 27 SEM_DETECCAO e 18 AMBIGUAS; taxa correta global bruta 92,72%.",
    ]
    for number, name in enumerate(("A", "B", "C", "D", "E"), start=4):
        row = grid_by_id[references[name]]
        titles = {
            "A": "Modelo bruto", "B": "Apenas ROI", "C": "ROI + confidence 0.90",
            "D": "ROI + confidence 0.90 + margin 0.10", "E": "Política muito conservadora",
        }
        report.extend([
            "", f"## {number}. Cenário {name} — {titles[name]}", "",
            f"- Política: `{row['PolicyId']}`", f"- {format_reference(row)}",
            f"- Sem a imagem corrompida: Correct={row['WithoutCorruptedCorrectAccept']}, "
            f"Wrong={row['WithoutCorruptedWrongAccept']}, NoDetection={row['WithoutCorruptedNoDetection']}, "
            f"LowConfidence={row['WithoutCorruptedLowConfidence']}, Ambiguous={row['WithoutCorruptedAmbiguous']}, "
            f"Coverage={float(row['WithoutCorruptedCoverage']) * 100:.2f}%, "
            f"AcceptedAccuracy={float(row['WithoutCorruptedAcceptedAccuracy']) * 100:.2f}%",
        ])

    report.extend([
        "", "## 9. Top 15", "",
        "| ROI | MinConfidence | MinMargin | CorrectAccept | WrongAccept | NoDetection | LowConfidence | Ambiguous | Coverage | AcceptedAccuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in top15:
        report.append(
            f"| {row['ROI']} | {row['MinConfidence']} | {row['MinMargin']} | "
            f"{row['CorrectAccept']} | {row['WrongAccept']} | {row['RejectNoDetection']} | "
            f"{row['RejectLowConfidence']} | {row['RejectAmbiguous']} | "
            f"{float(row['Coverage']) * 100:.2f}% | {float(row['AcceptedAccuracy']) * 100:.2f}% |"
        )
    report.extend([
        "", "## 10. Pareto", "",
        f"- Políticas não dominadas: {len(pareto)}.",
    ])
    for row in pareto:
        report.append(
            f"- `{row['PolicyId']}` — Wrong={row['WrongAccept']}, "
            f"AcceptedAccuracy={float(row['AcceptedAccuracy']) * 100:.2f}%, "
            f"Coverage={float(row['Coverage']) * 100:.2f}%."
        )
    report.extend([
        "", "## 11. Ambiguidades 045", "",
        "| Cenário | ACCEPT_045 | REJECT_NO_DETECTION | REJECT_LOW_CONFIDENCE | REJECT_AMBIGUOUS | WRONG_ACCEPT |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in amb045_reference:
        report.append(
            f"| {row['Scenario']} | {row['Accept045']} | {row['RejectNoDetection']} | "
            f"{row['RejectLowConfidence']} | {row['RejectAmbiguous']} | {row['WrongAccept']} |"
        )
    report.extend([
        "", "## 12. Ambiguidade 031", "",
        "- Para confidence de 0.50 a 0.90, margens 0.00 e 0.05 aceitam 031; margens de 0.10 a 0.30 rejeitam como ambígua.",
        "- Em confidence 0.95, a box 045 de 0.921875 é removida e a 031 de 0.992188 é aceita em todas as margens testadas.",
        "- ROI_CENTER e ROI_INTERSECTION_50 não alteram esse caso: ambas as boxes passam pelas duas regras espaciais.",
        "", "## 13. Falsos negativos", "",
        "- `031/foto0286.jpg`, `foto0287.jpg`, `foto0288.jpg` e `foto0290.jpg` permaneceram REJECT_NO_DETECTION nas 147 políticas.",
        "- Total verificado: 588/588 decisões fail-safe; nenhuma classificação foi inventada.",
        "", "## 14. Imagem corrompida", "",
        "- `045/foto0062.jpg` permaneceu REJECT_NO_DETECTION nas 147 políticas.",
        "- WITH_CORRUPTED_IMAGE usa 618 imagens; WITHOUT_CORRUPTED_IMAGE usa 617. A remoção altera somente o denominador e reduz NoDetection em uma unidade.",
        "", "## 15. Conclusão", "",
        "ROI TEM BENEFÍCIO LIMITADO", "",
        "A ROI remove as boxes secundárias de várias ambiguidades, mas neste conjunto o simples uso do maior score já produz zero WRONG_ACCEPT e maior coverage. A confiança e a margem aumentam rejeições sem melhorar accepted_accuracy, que já é 100% entre os aceites retrospectivos. Isso não demonstra segurança futura: não houve classificações cruzadas brutas neste conjunto.",
        "", "Esses parâmetros foram avaliados no mesmo conjunto usado para derivar a ROI e analisar os erros. Portanto, não podem ser considerados calibrados para produção.",
        "", "## 16. Próximo passo", "",
        "COLETAR CONJUNTO INDEPENDENTE PARA VALIDAR A POLÍTICA",
    ])
    (OUTPUT / "policy_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({
        "baseline": baseline, "policies": len(grid), "per_image": len(per_image),
        "wrong_accept_policies": sum(int(row["WrongAccept"]) > 0 for row in grid),
        "pareto": len(pareto), "output": str(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
