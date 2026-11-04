# JupyterLab

A minimal JupyterLab with base packages and capability managed with [pixi](https://pixi.sh).

## Usage

### Launch with default directory

```sh
pixi run launch
```

### Launch with a specific directory

```sh
pixi run launch -- ~/my-notebooks
```

## Known issue: polars network reads

No polars 1.x release includes the fix for the [October 2026 eMudhra incident](https://emudhra.we-have-a-problem.com/). The polars locked here (1.39.3) can verify HTTPS with `rustls-webpki` 0.103.9, a Rust certificate verifier older than 0.103.16, the first release that rejects the compromised keys. That verifier uses the operating system's root certificates, but not the operating system's own block of the compromised CAs. So polars may accept a certificate the rest of the system rejects. This only affects polars reading cloud storage or `https://` URLs itself (for example, `pl.read_csv("https://…")`). Local files, pandas, and the rest of the environment are not affected. To read from the network until this is fixed, download with another library first (for example, `requests` or `urllib`, which use the patched Python) and pass the data to polars. polars 2.1.0 has the fix. This capability stays on polars 1.x for now so that existing notebooks keep working.
