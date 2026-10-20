"""UDFs for the balloon flight ops CLI (pure Python, no table imports)."""

from __future__ import annotations

import datetime as dt

import pixeltable as pxt
from pixeltable.utils.project import digest

PROPANE_KG_PER_BURN_SECOND = 0.11  # burner consumption for a 4-burner basket at full flame (re-measured)
STANDARD_PASSENGER_KG = 85.0  # used when a manifest entry has no weight


@pxt.udf
def flight_minutes(launch_at: dt.datetime, landing_at: dt.datetime) -> float:
    """Flight time in minutes between launch and landing."""
    return round((landing_at - launch_at).total_seconds() / 60.0, 1)


@pxt.udf
def burn_seconds(burner_log: pxt.Json) -> float:
    """Total burner time in seconds from the basket logger's list of burns.

    The logger writes each burn as {"t": "<mm:ss into the flight>", "secs": <burn length>}.
    """
    return round(sum(float(b['secs']) for b in burner_log), 1)


@pxt.udf
def fuel_kg(burn_secs: float) -> float:
    """Propane used, estimated from total burn time."""
    return round(burn_secs * PROPANE_KG_PER_BURN_SECOND, 1)


@pxt.udf
def payload_kg(manifest: pxt.Json) -> float:
    """Passenger payload: the sum of the manifest weights (standard weight for a missing one)."""
    return round(sum(float(p.get('kg') or STANDARD_PASSENGER_KG) for p in manifest), 1)


@pxt.udf
def wind_band(wind_kts: float) -> str:
    """Launch wind band used in the operator's go/no-go briefing."""
    if wind_kts < 4:
        return 'calm'
    if wind_kts < 8:
        return 'light'
    if wind_kts <= 12:
        return 'marginal'
    return 'no-go'


@pxt.udf
def manifest_digest(flight_id: str, launch_at: dt.datetime, manifest: pxt.Json) -> str:
    """Stable content hash of a flight record: same flight + same manifest -> same digest, on any machine.

    Uses pixeltable.utils.project.digest(): SHA-256 of canonical JSON (sorted keys, no whitespace).
    """
    return digest({'flight': flight_id, 'launch_at': launch_at.isoformat(), 'manifest': manifest})
