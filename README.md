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

This repo ships a [`pixi.toml`](pixi.toml), so you can run the script in a managed environment straight from this clone:

```
pixi run make-tm4 -- <experiment_folder>
pixi run make-tm4 -- <experiment_folder> --segmentation <experiment_folder>/cellposeMosaic.geojson
```

To use the script from another project that has its own `pixi.toml`, add a task pointing at the script and declare the dependencies in that project:

```toml
# pixi.toml of your own project
[tasks]
make-tm4 = "python /path/to/tissuumapPrep-v4/scripts/make_tissuumaps_v4.py"

[dependencies]
python = ">=3.10"
# only needed for --segmentation:
pandas = "*"
geopandas = "*"
anndata = "*"
scanpy = "*"
leidenalg = "*"
```

```
pixi run make-tm4 -- experiments/20240925CA-01
pixi run make-tm4 -- experiments/20240925CA-01 --segmentation experiments/20240925CA-01/cellposeMosaic.geojson
```

Replace `/path/to/tissuumapPrep-v4` with the location of your clone (a relative path works too). Alternatively, run the task from this repo's pixi environment in any directory: `pixi run --manifest-path /path/to/tissuumapPrep-v4/pixi.toml make-tm4 -- <experiment_folder>`.
