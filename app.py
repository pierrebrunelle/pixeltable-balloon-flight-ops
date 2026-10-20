"""Hot-air balloon flight ops CLI built with Pixeltable.

A balloon operator's flight log: envelopes (the balloons), flights with the basket
logger's burner log and the passenger manifest, and an import log. Computed columns
derive flight time, burn time, propane used, payload, the launch-wind band and a stable
manifest digest (pixeltable.utils.project.digest), so re-importing the same batch file
never duplicates a flight. `python cli.py` is the operator's command line: import
batches, logbooks per pilot and envelope, an overweight check, and `fingerprint`, which
recomputes the project fingerprint with the public hashing helpers (digest, member_hash,
pyproject_hash) to show which files a cloud deploy would upload.

Layout: UDFs live in udfs.py; this file holds the table models; cli.py builds the
queries. No HTTP router.

    pxt schema update app.py balloons
    python seed.py
    python cli.py import data/batch_*.json
    python cli.py logbook "R. Okafor"
"""

from __future__ import annotations

import pixeltable as pxt

from udfs import burn_seconds, flight_minutes, fuel_kg, manifest_digest, payload_kg, wind_band

TableModel = pxt.model_base()


class Envelopes(TableModel, name='envelopes'):
    """One balloon envelope: registration, size, passenger limit and hours since the last inspection."""

    registration = pxt.Column(type=pxt.String, primary_key=True)
    maker: pxt.String
    volume_m3: pxt.Int
    max_passengers: pxt.Int
    max_payload_kg: pxt.Float
    hours_since_inspection: pxt.Float


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


class Imports(TableModel, name='imports'):
    """One imported batch file, keyed by its content hash (pixeltable.utils.project.member_hash)."""

    file_hash = pxt.Column(type=pxt.String, primary_key=True)
    file_name: pxt.String
    flights: pxt.Int
    imported_at: pxt.Timestamp
