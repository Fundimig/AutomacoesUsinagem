"""Ponto de entrada para a futura auditoria do dataset Edge Impulse."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida a localização de um dataset exportado. "
            "O parser será implementado depois que o formato real for obtido."
        )
    )
    parser.add_argument("dataset_path", type=Path, help="Arquivo ou pasta do dataset exportado")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = args.dataset_path.expanduser()

    if not dataset_path.exists():
        print(f"ERROR: dataset artifact not found: {dataset_path}")
        return 2

    print(f"Dataset artifact located: {dataset_path.resolve()}")
    print("No dataset parser is configured because the real export format is not available yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
