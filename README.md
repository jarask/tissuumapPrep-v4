# tissuumapPrep
 Scripts for preparing files from MERFISH to TissUUmaps

## Scripts

- `scripts/convert2tmap.ipynb` — notebook converting MERFISH output (spots, segmentation, mosaic image) to a TissUUmaps V3 `.tmap` file.
- `scripts/make_tissuumaps_v4.py` — builds a shareable TissUUmaps V4 `.tm4` project from a MERFISH (Merlin) experiment folder:

  ```
  python scripts/make_tissuumaps_v4.py <experiment_folder>
  ```

  The experiment folder (named by the experiment ID) must contain `ExportBarcodes/barcodes.csv` (with `gene`, `x_pixel` and `y_pixel` columns) and `GenerateMosaic/mosaic_polyt.png`. The script copies both files into `<experiment_folder>/<experiment_id>_tissuumaps/`, writes `<experiment_id>.tm4` there (points use `x="y_pixel"`, `y="x_pixel"`, colored by the `gene` column with the `Distinct` palette), and zips the folder to `<experiment_folder>/<experiment_id>_tissuumaps.zip`. Unzip and open the `.tm4` file in TissUUmaps V4 to view the data.

  Optionally, pass a cell segmentation GeoJSON to also add the cell polygons as shapes, colored by Leiden cluster after a Scanpy UMAP (same pipeline as `convert2tmap.ipynb`):

  ```
  python scripts/make_tissuumaps_v4.py <experiment_folder> --segmentation <experiment_folder>/cellposeMosaic.geojson
  ```

  This adds the segmentation file (with a per-cell `id`) and a `cells.csv` (`id`, `leiden`) to the output folder and references them from the `.tm4` as a `geojson` shapes object with a `leiden` color map. It requires the optional dependencies `pandas`, `geopandas`, `anndata`, `scanpy` and `leidenalg`.

## Running with pixi

This repo ships a [`pixi.toml`](pixi.toml) with a `make-tm4` task, so from this clone:

```
pixi run make-tm4 -- <experiment_folder>
```

To use the script from another project that has its own `pixi.toml`, copy `scripts/make_tissuumaps_v4.py` into that project (or point the task at your clone of this repo) and add:

```toml
# pixi.toml of your own project
[tasks]
make-tm4 = "python scripts/make_tissuumaps_v4.py"
```

```
pixi run make-tm4 -- experiments/20240925CA-01
```

The base version is stdlib-only, so no extra dependencies are needed. Alternatively, run it from this repo's pixi environment in any directory: `pixi run --manifest-path /path/to/tissuumapPrep-v4/pixi.toml make-tm4 -- <experiment_folder>`.

Note: `--segmentation` (UMAP/Leiden cell labels) additionally requires `pandas`, `geopandas`, `anndata`, `scanpy` and `leidenalg` in the environment; the base version above does not.
