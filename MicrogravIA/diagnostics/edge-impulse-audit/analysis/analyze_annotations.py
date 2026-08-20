"""Ponto de entrada para a futura auditoria das annotations Edge Impulse."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida a localização de annotations exportadas. "
            "O parser será implementado depois que o formato real for obtido."
        )
    )
    parser.add_argument(
        "annotations_path",
        type=Path,
        help="Arquivo ou pasta contendo as annotations originais",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    annotations_path = args.annotations_path.expanduser()

    if not annotations_path.exists():
        print(f"ERROR: annotations artifact not found: {annotations_path}")
        return 2

    print(f"Annotations artifact located: {annotations_path.resolve()}")
    print("No annotations parser is configured because the real export format is not available yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
