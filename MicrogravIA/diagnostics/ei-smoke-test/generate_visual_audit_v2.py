#!/usr/bin/env python3
"""Generate exact-model-input diagnostic panels and contact sheets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results_v2"
AUDIT = RESULTS / "audit_visual"
IMAGE_ROOT = Path(
    r"C:\Users\marcel.silva\Fundimig\Usinagem - ED\Publica\Desenvolvimento"
    r"\Automação Usinagem\Micropulsionador\ImagensParaIA"
)

COLORS = {"031": (255, 48, 48), "045": (0, 220, 255)}
MODEL_SIZE = (160, 160)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


FONTS = {
    "title": font(30, True), "head": font(23, True), "body": font(19),
    "small": font(15), "tiny": font(12), "box": font(14, True),
}


def fit(image: Image.Image, size: tuple[int, int], background=(25, 25, 25)) -> tuple[Image.Image, tuple[int, int, int, int]]:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    x = (size[0] - copy.width) // 2
    y = (size[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas, (x, y, copy.width, copy.height)


def load_annotations(name: str, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    path = AUDIT / name
    if not path.is_file():
        return {}
    return {tuple(row[field] for field in key_fields): row for row in read_csv(path)}


def box_text(box: dict[str, str]) -> str:
    confidence = float(box["Confidence"].replace(",", "."))
    return (f"{box['Label']} {confidence:.6f}  "
            f"x={box['X']} y={box['Y']} w={box['W']} h={box['H']}")


def draw_box_on_model(draw: ImageDraw.ImageDraw, box: dict[str, str], origin: tuple[int, int], scale: int) -> None:
    x = origin[0] + int(box["X"]) * scale
    y = origin[1] + int(box["Y"]) * scale
    w = int(box["W"]) * scale
    h = int(box["H"]) * scale
    color = COLORS.get(box["Label"], (255, 255, 0))
    draw.rectangle((x, y, x + w - 1, y + h - 1), outline=color, width=4)
    label = f"{box['Label']} {float(box['Confidence'].replace(',', '.')):.3f}"
    text_box = draw.textbbox((x, y), label, font=FONTS["box"])
    text_y = max(origin[1], y - (text_box[3] - text_box[1]) - 4)
    draw.rectangle((x, text_y, x + text_box[2] - text_box[0] + 5, y), fill=(0, 0, 0))
    draw.text((x + 2, text_y + 1), label, fill=color, font=FONTS["box"])


def draw_box_on_original(
    draw: ImageDraw.ImageDraw,
    box: dict[str, str],
    displayed: tuple[int, int, int, int],
    source_size: tuple[int, int],
) -> None:
    origin_x, origin_y, display_w, display_h = displayed
    model_x, model_y = int(box["X"]), int(box["Y"])
    model_w, model_h = int(box["W"]), int(box["H"])
    # FIT_LONGEST metadata: 160x120 image at y=20 inside 160x160.
    sx0 = model_x / 160.0 * source_size[0]
    sy0 = (model_y - 20) / 120.0 * source_size[1]
    sx1 = (model_x + model_w) / 160.0 * source_size[0]
    sy1 = (model_y + model_h - 20) / 120.0 * source_size[1]
    x0 = origin_x + sx0 / source_size[0] * display_w
    y0 = origin_y + sy0 / source_size[1] * display_h
    x1 = origin_x + sx1 / source_size[0] * display_w
    y1 = origin_y + sy1 / source_size[1] * display_h
    color = COLORS.get(box["Label"], (255, 255, 0))
    draw.rectangle((x0, y0, x1, y1), outline=color, width=5)


def make_panel(
    row: dict[str, str],
    model_input: Image.Image,
    boxes: list[dict[str, str]],
    image_annotation: dict[str, str],
    box_annotations: dict[tuple[str, str], dict[str, str]],
) -> Image.Image:
    source_path = IMAGE_ROOT / Path(row["File"])
    with Image.open(source_path) as opened:
        original = ImageOps.exif_transpose(opened).convert("RGB")

    panel = Image.new("RGB", (1600, 950), (18, 18, 22))
    draw = ImageDraw.Draw(panel)
    draw.text((30, 20), f"ID {row['Id']} — {row['File']}", fill="white", font=FONTS["title"])
    detected = row["Detected"] if row["Detected"] else "NONE"
    header = (f"expected={row['Expected']}  detected={detected}  "
              f"confidence={row['Confidence'] or '0'}  "
              f"result={row['Result']}  boxes={row['Boxes']}")
    draw.text((30, 62), header, fill=(230, 230, 230), font=FONTS["body"])

    original_view, displayed = fit(original, (900, 675))
    panel.paste(original_view, (30, 110))
    original_displayed = (30 + displayed[0], 110 + displayed[1], displayed[2], displayed[3])
    draw.rectangle(
        (original_displayed[0], original_displayed[1],
         original_displayed[0] + original_displayed[2] - 1,
         original_displayed[1] + original_displayed[3] - 1),
        outline=(255, 170, 0), width=4,
    )
    for box in boxes:
        draw_box_on_original(draw, box, original_displayed, original.size)
    draw.text((30, 795), "ORIGINAL — 100% da imagem participa do FIT_LONGEST",
              fill=(255, 190, 60), font=FONTS["small"])

    preview = model_input.resize((640, 640), Image.Resampling.NEAREST)
    panel.paste(preview, (950, 110))
    draw.rectangle((950, 110, 1589, 749), outline=(210, 210, 210), width=2)
    draw.rectangle((950, 110, 1589, 189), outline=(255, 170, 0), width=3)
    draw.rectangle((950, 670, 1589, 749), outline=(255, 170, 0), width=3)
    draw.text((960, 116), "PADDING 20 px", fill=(255, 190, 60), font=FONTS["small"])
    draw.text((950, 765), "MODEL INPUT 160×160 — conteúdo 160×120, padding y=20",
              fill=(230, 230, 230), font=FONTS["small"])

    for box in boxes:
        draw_box_on_model(draw, box, (950, 110), 4)

    if row["Result"] == "SEM_DETECCAO":
        message = "NO DETECTION"
        bounds = draw.textbbox((0, 0), message, font=FONTS["title"])
        x = 950 + (640 - (bounds[2] - bounds[0])) // 2
        draw.rectangle((x - 12, 405, x + bounds[2] - bounds[0] + 12, 455), fill=(0, 0, 0))
        draw.text((x, 412), message, fill=(255, 60, 60), font=FONTS["title"])

    cause = image_annotation.get("PrimaryCause", "INDETERMINADO")
    observation = image_annotation.get("Observation", "Auditoria visual pendente")
    draw.text((30, 830), f"CAUSA PRINCIPAL: {cause}", fill=(255, 230, 100), font=FONTS["head"])
    draw.text((30, 865), observation, fill=(235, 235, 235), font=FONTS["body"])
    y = 805
    for box in boxes:
        location = box_annotations.get((row["Id"], box["Index"]), {}).get(
            "VisualLocation", "INDETERMINADA")
        draw.text((950, y), f"box {box['Index']}: {box_text(box)} — {location}",
                  fill=COLORS.get(box["Label"], "yellow"), font=FONTS["small"])
        y += 25
    return panel


def make_contact_sheet(
    title: str,
    selected: Iterable[dict[str, str]],
    panels: dict[str, Image.Image],
    output: Path,
    columns: int,
) -> None:
    rows = list(selected)
    tile_size = (760, 470)
    title_height = 70
    count_rows = max(1, (len(rows) + columns - 1) // columns)
    sheet = Image.new("RGB", (tile_size[0] * columns, title_height + tile_size[1] * count_rows), (12, 12, 15))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 15), f"{title} — {len(rows)} imagens", fill="white", font=FONTS["title"])
    for index, row in enumerate(rows):
        tile = panels[row["Id"]].copy()
        tile.thumbnail((tile_size[0] - 12, tile_size[1] - 12), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_size[0] + 6
        y = title_height + (index // columns) * tile_size[1] + 6
        sheet.paste(tile, (x, y))
    sheet.save(output, "JPEG", quality=92, subsampling=0)


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    individual = AUDIT / "individual"
    previews = AUDIT / "previews_160x160"
    individual.mkdir(exist_ok=True)
    previews.mkdir(exist_ok=True)

    problematic = read_csv(RESULTS / "batch_v2_problematic.csv")
    boxes = read_csv(RESULTS / "batch_v2_boxes.csv")
    manifest = read_csv(AUDIT / "model_inputs_manifest.csv")
    manifest_by_id = {row["Id"]: row for row in manifest}
    boxes_by_id: dict[str, list[dict[str, str]]] = {}
    for box in boxes:
        boxes_by_id.setdefault(box["Id"], []).append(box)
    image_annotations = load_annotations("visual_image_annotations.csv", ("Id",))
    box_annotations = load_annotations("visual_box_annotations.csv", ("Id", "Index"))

    panels: dict[str, Image.Image] = {}
    audit_index: list[dict[str, str]] = []
    for row in problematic:
        item = manifest_by_id.get(row["Id"])
        if item is None:
            raise RuntimeError(f"Missing exact model input for ID {row['Id']}")
        rgb_path = AUDIT / item["RgbFile"]
        data = rgb_path.read_bytes()
        if len(data) != 160 * 160 * 3:
            raise RuntimeError(f"Invalid RGB fixture length for ID {row['Id']}")
        model_input = Image.frombytes("RGB", MODEL_SIZE, data)
        safe_name = f"{int(row['Id']):04d}_{row['Expected']}_{Path(row['File']).stem}"
        preview_path = previews / f"{safe_name}.png"
        model_input.save(preview_path, "PNG")
        image_annotation = image_annotations.get((row["Id"],), {})
        row_boxes = boxes_by_id.get(row["Id"], [])
        panel = make_panel(row, model_input, row_boxes, image_annotation, box_annotations)
        panel_path = individual / f"{safe_name}.jpg"
        panel.save(panel_path, "JPEG", quality=94, subsampling=0)
        panels[row["Id"]] = panel
        audit_index.append({
            "Id": row["Id"], "File": row["File"], "Expected": row["Expected"],
            "Detected": row["Detected"], "Confidence": row["Confidence"],
            "Result": row["Result"], "Boxes": row["Boxes"],
            "PrimaryCause": image_annotation.get("PrimaryCause", "INDETERMINADO"),
            "Observation": image_annotation.get("Observation", ""),
            "Preview": preview_path.relative_to(AUDIT).as_posix(),
            "Diagnostic": panel_path.relative_to(AUDIT).as_posix(),
        })

    categories = [
        ("031 — SEM_DETECCAO", lambda row: row["Expected"] == "031" and row["Result"] == "SEM_DETECCAO", "031_no_detection.jpg", 2),
        ("045 — SEM_DETECCAO", lambda row: row["Expected"] == "045" and row["Result"] == "SEM_DETECCAO", "045_no_detection.jpg", 1),
        ("031 — AMBIGUA", lambda row: row["Expected"] == "031" and row["Result"] == "AMBIGUA", "031_ambiguous.jpg", 1),
        ("045 — AMBIGUA", lambda row: row["Expected"] == "045" and row["Result"] == "AMBIGUA", "045_ambiguous.jpg", 2),
        ("TODOS OS CASOS PROBLEMÁTICOS", lambda row: True, "all_problematic.jpg", 3),
    ]
    for title, predicate, name, columns in categories:
        make_contact_sheet(title, (row for row in problematic if predicate(row)), panels, AUDIT / name, columns)

    fields = list(audit_index[0])
    with (AUDIT / "visual_audit_index.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_index)

    print(f"VISUAL_AUDIT_GENERATED|images={len(audit_index)}|directory={AUDIT}")


if __name__ == "__main__":
    main()
