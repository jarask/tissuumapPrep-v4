"""Create a shareable TissUUmaps V4 (.tm4) project from MERFISH (Merlin) output.

Usage:
    python scripts/make_tissuumaps_v4.py <experiment_folder>

<experiment_folder> is the experiment ID folder and must contain:
    ExportBarcodes/barcodes.csv       barcodes with gene, x_pixel and y_pixel columns
    GenerateMosaic/mosaic_polyt.png   mosaic image

The script copies both files into <experiment_folder>/<experiment_id>_tissuumaps/,
writes <experiment_id>.tm4 there, and zips the folder to
<experiment_folder>/<experiment_id>_tissuumaps.zip for sharing.
"""

import argparse
import csv
import json
import shutil
import sys
import zipfile
from pathlib import Path

BARCODES_RELPATH = Path("ExportBarcodes") / "barcodes.csv"
MOSAIC_RELPATH = Path("GenerateMosaic") / "mosaic_polyt.png"
TM4_SUFFIX = ".tm4"
DISTINCT_PALETTE = "distinct"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert MERFISH (Merlin) output to a TissUUmaps V4 (.tm4) "
        "project and zip it for sharing."
    )
    parser.add_argument(
        "experiment_folder",
        type=Path,
        help="Experiment folder (named by the experiment ID) containing "
        "ExportBarcodes/barcodes.csv and GenerateMosaic/mosaic_polyt.png",
    )
    parser.add_argument(
        "--barcodes",
        type=Path,
        default=None,
        help="Path to barcodes.csv (default: <experiment_folder>/ExportBarcodes/barcodes.csv)",
    )
    parser.add_argument(
        "--mosaic",
        type=Path,
        default=None,
        help="Path to the mosaic image (default: <experiment_folder>/GenerateMosaic/mosaic_polyt.png)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output folder (default: <experiment_folder>/<experiment_id>_tissuumaps)",
    )
    parser.add_argument("--x-column", default="y_pixel", help="barcodes.csv column used as point X (default: y_pixel)")
    parser.add_argument("--y-column", default="x_pixel", help="barcodes.csv column used as point Y (default: x_pixel)")
    parser.add_argument("--gene-column", default="gene", help="barcodes.csv column used for point coloring (default: gene)")
    return parser.parse_args(argv)


def require_file(path, what):
    if not path.is_file():
        sys.exit(f"Error: {what} not found: {path}")
    return path


def check_columns(barcodes_csv, x_column, y_column, gene_column):
    with open(barcodes_csv, newline="", encoding="utf-8-sig") as f:
        header = next(csv.reader(f), [])
    missing = [c for c in (x_column, y_column, gene_column) if c not in header]
    if missing:
        sys.exit(
            f"Error: {barcodes_csv} is missing column(s) {missing}. "
            f"Available columns: {header}"
        )


def build_project(experiment_id, barcodes_name, mosaic_name, x_column, y_column, gene_column):
    return {
        "name": experiment_id,
        "layers": [{"id": "layer", "name": experiment_id}],
        "images": [
            {
                "id": "mosaic",
                "name": mosaic_name,
                "layer": "layer",
                "dataSource": {"type": "image", "source": mosaic_name},
            }
        ],
        "tables": [
            {
                "id": "barcodes-table",
                "name": barcodes_name,
                "dataSource": {"type": "csv", "source": barcodes_name},
            }
        ],
        "points": [
            {
                "id": "barcodes",
                "name": barcodes_name,
                "layer": "layer",
                "dataSource": {
                    "type": "table",
                    "table": "barcodes-table",
                    "x": x_column,
                    "y": y_column,
                },
                "pointColor": {
                    "groupBy": {"column": gene_column, "palette": DISTINCT_PALETTE}
                },
            }
        ],
    }


def main(argv=None):
    args = parse_args(argv)

    experiment_dir = args.experiment_folder
    if not experiment_dir.is_dir():
        sys.exit(f"Error: experiment folder not found: {experiment_dir}")
    experiment_id = experiment_dir.name or experiment_dir.resolve().name

    barcodes_csv = require_file(
        args.barcodes or experiment_dir / BARCODES_RELPATH, "barcodes.csv"
    )
    mosaic_png = require_file(
        args.mosaic or experiment_dir / MOSAIC_RELPATH, "mosaic image"
    )
    check_columns(barcodes_csv, args.x_column, args.y_column, args.gene_column)

    out_dir = args.out_dir or experiment_dir / f"{experiment_id}_tissuumaps"
    out_dir.mkdir(parents=True, exist_ok=True)

    barcodes_name = barcodes_csv.name
    mosaic_name = mosaic_png.name
    shutil.copy2(barcodes_csv, out_dir / barcodes_name)
    shutil.copy2(mosaic_png, out_dir / mosaic_name)

    tm4_path = out_dir / f"{experiment_id}{TM4_SUFFIX}"
    project = build_project(
        experiment_id, barcodes_name, mosaic_name, args.x_column, args.y_column, args.gene_column
    )
    with open(tm4_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2)

    zip_path = out_dir.parent / f"{out_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in sorted(out_dir.iterdir()):
            if file_path.is_file():
                zipf.write(file_path, f"{out_dir.name}/{file_path.name}")

    print(f"TissUUmaps V4 project folder: {out_dir}")
    print(f"  project file: {tm4_path}")
    print(f"  data files:   {barcodes_name}, {mosaic_name}")
    print(f"Shared archive: {zip_path}")


if __name__ == "__main__":
    main()
