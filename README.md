<!-- pixeltable-example-app: 20261020-balloon-flight-ops -->
# Hot-Air Balloon Flight Ops CLI built with Pixeltable

![Hot-Air Balloon Flight Ops CLI built with Pixeltable](.github/social-preview.png)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pierrebrunelle/pixeltable-balloon-flight-ops?quickstart=1)
[![Built with Pixeltable](https://img.shields.io/badge/built%20with-Pixeltable-5b4bff)](https://pixeltable.com)
[![PyPI - pixeltable](https://img.shields.io/pypi/v/pixeltable?label=pixeltable)](https://pypi.org/project/pixeltable/)
[![GitHub stars](https://img.shields.io/github/stars/pixeltable/pixeltable?style=social)](https://github.com/pixeltable/pixeltable)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

`Envelopes`, `Flights` and `Imports` hold a balloon operator's flight log. Each flight carries the basket logger's burner log and the passenger manifest as JSON; computed columns derive flight minutes, total burn time, propane used, payload, the launch-wind band and a stable `record_digest` built with `pixeltable.utils.project.digest()` (SHA-256 of canonical JSON). `cli.py` is the operator's command line (argparse, no HTTP router): `import` reads batch files and skips any file whose content hash (`member_hash()` over the file's SHA-256) is already in `Imports` and any flight already in the log, so re-running an import is always safe; `logbook`, `envelope`, `windy` and `overweight` are queries over the tables; `fingerprint` recomputes the archive part of the project fingerprint from the file bytes with the public helpers `digest()`, `member_hash()` and `pyproject_hash()` and checks it against Pixeltable's own, so you can see exactly which files `pxt db update` would upload to Pixeltable Cloud.

[Pixeltable](https://pixeltable.com) is open-source, Python-native **multimodal AI data infrastructure**: tables, incremental computed columns, UDFs, indexes and serving in one library, running locally or on Pixeltable Cloud.

> ⭐ **Like this example?** Star [pixeltable/pixeltable](https://github.com/pixeltable/pixeltable) on GitHub. It helps other developers find it.

## What this example shows

- **`pxt` CLI and local dashboard** for exploring tables and computed columns
- **Incremental computed columns** powered by plain Python UDFs (`@pxt.udf`)
- **B-tree indexes** declared on the model (`__indexes__`) back the lookup queries
- **`pixeltable.toml` project config**: local and Pixeltable Cloud database sizing in one file
- **Pixeltable Cloud lifecycle** from the `pxt` CLI (`db`, `schema`, `service`)
- **Importable UDF module**: UDFs live in `udfs.py`; tables and queries live in `app.py` (Pixeltable resolves UDFs by module path)
- **`pixeltable.toml`** declares a local database and a **Pixeltable Cloud** database, so the same code deploys with `pxt db update`

## Recovering from a bad import

| Situation | What to run |
|---|---|
| A batch with a mistyped manifest went in (`cli.py overweight` exits 1) | `pxt history balloons/flights` then `pxt revert balloons/flights -f` and `pxt revert balloons/imports -f`; import the corrected file |
| The import process was killed half way | Nothing to clean up: an insert is one transaction, so the table is at the previous version. Run the same `cli.py import` again |
| The same file is imported twice | Skipped by its content hash in `Imports`; flights already in the log are skipped by `flight_id` |
| Archive last season under another name | `pxt rename balloons balloons_2026q3`, then `pxt schema update app.py balloons` for a fresh log; `BALLOONS_DIR=balloons_2026q3 python cli.py ...` reads the archive |

`pxt revert` asks for confirmation on a terminal and refuses without `-f` when there is none; `-n` prints what it would undo.

## How the fingerprint is computed

`pxt db update` uploads the project files that the database entry's `exclude` list keeps, and compares a fingerprint of them with the deployed one. `python cli.py fingerprint` rebuilds the archive part from the bytes on disk with the public helpers in `pixeltable.utils.project`:

```python
from pixeltable.utils.project import digest, member_hash, pyproject_hash

files = {rel: member_hash(sha256(bytes).hexdigest(), symlink=False) for rel, bytes in project_files}
# pyproject.toml is hashed with pyproject_hash(), which ignores the [tool.pixeltable] table
archive_digest = digest(files)  # SHA-256 of canonical JSON
```

and prints `matches_pxt: True` when it agrees with `project_fingerprint().archive_digest()`. With `--db pxt://<org>:<db>` it also prints `pxt db diff --json` for that database.

## Notes

- `digest()` takes JSON values only: convert datetimes with `isoformat()` first (the `manifest_digest` UDF does).
- Comments, key order and the `[tool.pixeltable]` table do not change `pyproject_hash()`; a dependency change does.
- The CLI builds its queries from the tables in Python (`flights.where(...).select(...)`), so it runs unchanged against a local catalog, a local proxy started with `pxt localproxy start` or Pixeltable Cloud.

## What's inside

| File | What it is |
|------|------------|
| `.devcontainer/devcontainer.json` | GitHub Codespaces / Dev Container config: Python 3.12, installs `requirements.txt` |
| `.github/social-preview.png` | Social preview image (1280x640) |
| `CITATION.cff` | Citation metadata (authors, license, release date, keywords) |
| `app.py` | Tables declared as Python classes and `@pxt.query` functions |
| `cli.py` | Balloon flight ops: the operator's command line over the Pixeltable flight log |
| `data/batch_01.json` | Sample data |
| `data/batch_02.json` | Sample data |
| `data/batch_03.json` | Sample data |
| `data/batch_04.json` | Sample data |
| `data/batch_04_bad.json` | Sample data |
| `pixeltable.toml` | Project config: the local database plus a Pixeltable Cloud database (sizing, deploy excludes) |
| `seed.py` | Seed the balloon flight log: 4 envelopes, and 3 batch files of flights in data/ for `cli.py import` |
| `udfs.py` | Pixeltable UDFs (`@pxt.udf`) in their own importable module, imported by `app.py` |
| `requirements.txt` / `pyproject.toml` | Dependencies (`pixeltable>=0.7.19`) |

**Tables**

| Table | Stored columns | Computed columns |
|-------|---------|------------------|
| `envelopes` | `registration`, `maker`, `volume_m3`, `max_passengers`, `max_payload_kg`, `hours_since_inspection` | - |
| `flights` | `flight_id`, `registration`, `pilot`, `launch_site`, `launch_at`, `landing_at`, `wind_kts`, `burner_log`, `manifest`, `batch` | `minutes`, `burn_secs`, `propane_kg`, `payload`, `wind`, `record_digest` |
| `imports` | `file_hash`, `file_name`, `flights`, `imported_at` | - |

## Run in your browser (GitHub Codespaces)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pierrebrunelle/pixeltable-balloon-flight-ops?quickstart=1)

1. Click **Open in GitHub Codespaces** above (or [this link](https://codespaces.new/pierrebrunelle/pixeltable-balloon-flight-ops?quickstart=1)). The dev container installs Python 3.12 and `pixeltable>=0.7.19` from `requirements.txt`.
2. In the codespace terminal, create the tables, seed them and run the app:

   ```bash
   pxt schema update app.py balloons
   python seed.py                              # 4 envelopes; writes data/batch_01..03.json
   python cli.py import data/batch_*.json      # idempotent: run it twice, the second run skips every file
   python cli.py logbook "R. Okafor"           # one pilot's flights, newest first
   python cli.py overweight                    # exit 1 if any flight is over its envelope's limits
   python cli.py fingerprint                   # the files pxt would fingerprint, hashed with digest/member_hash/pyproject_hash
   pxt history balloons/flights                # one version per import; pxt revert balloons/flights -f undoes the last one
   ```


## Quickstart

Requires Python 3.11+ and `pixeltable>=0.7.19`.

```bash
git clone https://github.com/pierrebrunelle/pixeltable-balloon-flight-ops.git
cd pixeltable-balloon-flight-ops
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create the tables in a local catalog directory named `balloons`
pxt schema update app.py balloons

python seed.py                              # 4 envelopes; writes data/batch_01..03.json
python cli.py import data/batch_*.json      # idempotent: run it twice, the second run skips every file
python cli.py logbook "R. Okafor"           # one pilot's flights, newest first
python cli.py overweight                    # exit 1 if any flight is over its envelope's limits
python cli.py fingerprint                   # the files pxt would fingerprint, hashed with digest/member_hash/pyproject_hash
pxt history balloons/flights                # one version per import; pxt revert balloons/flights -f undoes the last one
```

## Deploy to Pixeltable Cloud

The same `app.py` runs on [Pixeltable Cloud](https://pixeltable.com). Sign in (or get a free trial database with `pxt new`), point the second database entry in `pixeltable.toml` at your own database, then deploy:

```bash
pxt login                       # or: export PIXELTABLE_API_KEY=<your-api-key>
# edit pixeltable.toml: name = 'pxt://<your-org>:<your-db>'
pxt db update pxt://<your-org>:<your-db>                 # build the image and upload the project
pxt schema update app.py pxt://<your-org>:<your-db>/balloons   # create the tables in the hosted database
```

Keep keys in environment variables or `pxt secret set`, never in code.

## Code walkthrough

**1. Business logic is plain Python, in `udfs.py`.** A `@pxt.udf` function can be used as a column expression. Pixeltable records UDFs by module path (`udfs.flight_minutes`), so they live in their own importable module rather than inline in the app: the daemon, serving workers and Pixeltable Cloud import it again by that path.

```python
# udfs.py
@pxt.udf
def flight_minutes(launch_at: dt.datetime, landing_at: dt.datetime) -> float:
    """Flight time in minutes between launch and landing."""
    return round((landing_at - launch_at).total_seconds() / 60.0, 1)
```

**2. Tables are Python classes (`app.py`).** Annotated attributes are stored columns; attributes assigned an expression are **computed columns** (`minutes`, `burn_secs`, `propane_kg`, `payload`, `wind`, `record_digest`), evaluated incrementally on every insert or update and recomputed when their inputs change. Indexes live next to the columns.

```python
# app.py
class Flights(TableModel, name='flights'):
    """One flight: envelope, pilot, launch site, times, launch wind, burner log and passenger manifest."""

    flight_id = pxt.Column(type=pxt.String, primary_key=True)
    registration: pxt.String
    pilot: pxt.String
    launch_site: pxt.String
    launch_at: pxt.Timestamp
    landing_at: pxt.Timestamp
    wind_kts: pxt.Float
    burner_log: pxt.Json
    manifest: pxt.Json
    batch: pxt.String

    minutes = flight_minutes(launch_at, landing_at)
    burn_secs = burn_seconds(burner_log)
    propane_kg = fuel_kg(burn_secs)
    payload = payload_kg(manifest)
    wind = wind_band(wind_kts)
    record_digest = manifest_digest(flight_id, launch_at, manifest)

    __indexes__ = [pxt.BtreeIndex(registration), pxt.BtreeIndex(pilot)]
```

## Learn more

- 🌐 Website: https://pixeltable.com
- 📚 Docs: https://docs.pixeltable.com
- 💻 Source: https://github.com/pixeltable/pixeltable (⭐ star it if Pixeltable is useful to you)
- 📦 PyPI: https://pypi.org/project/pixeltable/
- 🧩 More example apps: https://pierrebrunelle.github.io/awesome-pixeltable-apps/

**[More Pixeltable example apps →](https://pierrebrunelle.github.io/awesome-pixeltable-apps/)**

---

<sub>Built as part of a daily series of Pixeltable example apps · Pixeltable 0.7.19 · Python, incremental computed columns · Licensed under Apache-2.0.</sub>
