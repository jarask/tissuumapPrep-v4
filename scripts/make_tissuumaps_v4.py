"""Create a shareable TissUUmaps V4 (.tm4) project from MERFISH (Merlin) output.

Usage:
    python scripts/make_tissuumaps_v4.py <experiment_folder> [--segmentation SEG.geojson]

<experiment_folder> is the experiment ID folder and must contain:
    ExportBarcodes/barcodes.csv       barcodes with gene, x_pixel and y_pixel columns
    GenerateMosaic/mosaic_polyt.png   mosaic image

The script copies both files into <experiment_folder>/<experiment_id>_tissuumaps/,
writes <experiment_id>.tm4 there, and zips the folder to
<experiment_folder>/<experiment_id>_tissuumaps.zip for sharing.

With --segmentation, a cell segmentation GeoJSON (e.g. cellposeMosaic.geojson) is
added as shapes: barcodes are assigned to cells, a cell-by-gene matrix is computed
and clustered with Scanpy (UMAP + Leiden, as in convert2tmap.ipynb), and each cell
polygon is filled by its Leiden cluster. This option requires the optional
dependencies pandas, geopandas, anndata, scanpy and leidenalg.
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
CELLS_CSV_NAME = "cells.csv"
TAB10 = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]
UNCLUSTERED_COLOR = {"r": 128, "g": 128, "b": 128}


def hex_to_rgb(hex_color):
    return {
        "r": int(hex_color[1:3], 16),
        "g": int(hex_color[3:5], 16),
        "b": int(hex_color[5:7], 16),
    }


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
    parser.add_argument(
        "--segmentation",
        type=Path,
        default=None,
        help="Optional cell segmentation GeoJSON file (e.g. cellposeMosaic.geojson). "
        "Adds the cell polygons as shapes colored by Leiden cluster after UMAP. "
        "Requires pandas, geopandas, anndata and scanpy.",
    )
    parser.add_argument("--min-counts", type=int, default=5, help="Minimum transcripts per cell kept before clustering (default: 5)")
    parser.add_argument("--leiden-resolution", type=float, default=0.5, help="Leiden clustering resolution (default: 0.5)")
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


def build_project(
    experiment_id,
    barcodes_name,
    mosaic_name,
    x_column,
    y_column,
    gene_column,
    segmentation_name=None,
    color_map=None,
):
    project = {
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
    if segmentation_name is not None:
        project["tables"].append(
            {
                "id": "cells-table",
                "name": CELLS_CSV_NAME,
                "dataSource": {
                    "type": "csv",
                    "source": CELLS_CSV_NAME,
                    "idColumn": "id",
                },
            }
        )
        project["shapes"] = [
            {
                "id": "cells",
                "name": segmentation_name,
                "layer": "layer",
                "dataSource": {
                    "type": "geojson",
                    "source": segmentation_name,
                    "idProperty": "id",
                    "table": "cells-table",
                },
                "shapeFillColor": {
                    "groupBy": {"column": "leiden", "map": "leiden-colors"}
                },
                "shapeFillOpacity": {"constant": {"value": 0.4}},
                "shapeStrokeColor": {"constant": {"value": {"r": 0, "g": 0, "b": 0}}},
            }
        ]
        project["colorMaps"] = [color_map]
    return project


def run_segmentation(barcodes_csv, segmentation_path, gene_column, min_counts, leiden_resolution):
    import anndata
    import geopandas as gpd
    import pandas as pd
    import scanpy as sc

    spots = pd.read_csv(barcodes_csv)
    gdf = gpd.read_file(segmentation_path).reset_index(drop=True)
    if gdf.crs is not None and gdf.crs.is_geographic:
        gdf = gdf.set_crs(None, allow_override=True)

    spots_gdf = gpd.GeoDataFrame(
        spots, geometry=gpd.points_from_xy(spots["x_pixel"], spots["y_pixel"])
    )
    if gdf.crs is not None:
        spots_gdf = spots_gdf.set_crs(gdf.crs)
    spots_with_cells = gpd.sjoin(spots_gdf, gdf, how="inner", predicate="within")

    cell_gene_matrix = (
        spots_with_cells.groupby(["index_right", gene_column])
        .size()
        .unstack(fill_value=0)
        .reindex(gdf.index, fill_value=0)
    )

    gdf["centroid_x"] = gdf.geometry.centroid.x
    gdf["centroid_y"] = gdf.geometry.centroid.y
    adata = anndata.AnnData(
        cell_gene_matrix.to_numpy(),
        obsm={"spatial": gdf[["centroid_x", "centroid_y"]].to_numpy()},
    )
    adata.var_names = cell_gene_matrix.columns.to_numpy()

    try:
        sc.pp.filter_cells(adata, min_counts=min_counts)
        sc.pp.normalize_total(adata)
        sc.pp.log1p(adata)
        sc.pp.pca(adata)
        sc.pp.neighbors(adata)
        sc.tl.umap(adata)
        sc.tl.leiden(adata, resolution=leiden_resolution)
    except Exception as e:
        sys.exit(f"Error: UMAP/Leiden clustering failed: {e}")

    leiden_clusters = {
        int(k): int(v) for k, v in adata.obs["leiden"].to_dict().items()
    }
    gdf["leiden"] = gdf.index.map(leiden_clusters).fillna(-1).astype(int)
    gdf["id"] = gdf.index.astype(int)

    cells = pd.DataFrame({"id": gdf["id"], "leiden": gdf["leiden"]})
    return gdf, cells


def build_leiden_color_map(leiden_values):
    values = {}
    for v in sorted(set(leiden_values)):
        values[str(v)] = (
            UNCLUSTERED_COLOR if v == -1 else hex_to_rgb(TAB10[v % len(TAB10)])
        )
    return {
        "id": "leiden-colors",
        "name": "Leiden clusters",
        "values": values,
        "default": UNCLUSTERED_COLOR,
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

    segmentation_name = None
    color_map = None
    if args.segmentation is not None:
        seg_path = require_file(args.segmentation, "segmentation file")
        gdf, cells = run_segmentation(
            barcodes_csv,
            seg_path,
            args.gene_column,
            args.min_counts,
            args.leiden_resolution,
        )
        segmentation_name = seg_path.name
        gdf.to_file(out_dir / segmentation_name, driver="GeoJSON")
        cells.to_csv(out_dir / CELLS_CSV_NAME, index=False)
        color_map = build_leiden_color_map(cells["leiden"].tolist())

    tm4_path = out_dir / f"{experiment_id}{TM4_SUFFIX}"
    project = build_project(
        experiment_id,
        barcodes_name,
        mosaic_name,
        args.x_column,
        args.y_column,
        args.gene_column,
        segmentation_name=segmentation_name,
        color_map=color_map,
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
    data_files = [barcodes_name, mosaic_name]
    if segmentation_name is not None:
        data_files += [segmentation_name, CELLS_CSV_NAME]
    print(f"  data files:   {', '.join(data_files)}")
    print(f"Shared archive: {zip_path}")


if __name__ == "__main__":
    main()
