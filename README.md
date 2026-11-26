# tissuumapPrep
 Scripts for preparing files from MERFISH to TissUUmaps

## Scripts

- `scripts/convert2tmap.ipynb` — notebook converting MERFISH output (spots, segmentation, mosaic image) to a TissUUmaps V3 `.tmap` file.
- `scripts/make_tissuumaps_v4.py` — builds a shareable TissUUmaps V4 `.tm4` project from a MERFISH (Merlin) experiment folder:

  ```
  python scripts/make_tissuumaps_v4.py <experiment_folder>
  ```

  The experiment folder (named by the experiment ID) must contain `ExportBarcodes/barcodes.csv` (with `gene`, `x_pixel` and `y_pixel` columns) and `GenerateMosaic/mosaic_polyt.png`. The script copies both files into `<experiment_folder>/<experiment_id>_tissuumaps/`, writes `<experiment_id>.tm4` there (points use `x="y_pixel"`, `y="x_pixel"`, colored by the `gene` column with the `Distinct` palette), and zips the folder to `<experiment_folder>/<experiment_id>_tissuumaps.zip`. Unzip and open the `.tm4` file in TissUUmaps V4 to view the data.
