"""Ponto de entrada para a futura auditoria de métricas Edge Impulse."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Valida a localização de métricas exportadas. "
            "O parser será implementado depois que o formato real for obtido."
        )
    )
    parser.add_argument(
        "metrics_path",
        type=Path,
        help="Arquivo ou pasta contendo métricas originais",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics_path = args.metrics_path.expanduser()

    if not metrics_path.exists():
        print(f"ERROR: metrics artifact not found: {metrics_path}")
        return 2

    print(f"Metrics artifact located: {metrics_path.resolve()}")
    print("No metrics parser is configured because the real export format is not available yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
