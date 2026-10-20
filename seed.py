"""Seed the balloon flight log: 4 envelopes, and 3 batch files of flights in data/ for `cli.py import`.

    python seed.py            # inserts envelopes, writes data/batch_01.json .. batch_03.json
    BALLOONS_DIR=pxt://<org>:<db>/balloons python seed.py   # same, on a Pixeltable Cloud database
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random
from pathlib import Path

import pixeltable as pxt

from app import TableModel

TZ = dt.timezone(dt.timedelta(hours=-6))  # the operator flies on Mountain Daylight Time
SITES = ['Riverside Park', 'Old Mill Field', 'Mesa Overlook', 'Fairgrounds']
PILOTS = ['R. Okafor', 'L. Haugen', 'M. Duarte']
FIRST = ['Ana', 'Ben', 'Chloe', 'Dev', 'Eli', 'Fay', 'Gus', 'Hana', 'Ivo', 'Jun', 'Kai', 'Lena', 'Milo', 'Nia']

ENVELOPES = [
    {'registration': 'N451BA', 'maker': 'Cameron', 'volume_m3': 3400, 'max_passengers': 4, 'max_payload_kg': 420.0, 'hours_since_inspection': 61.5},
    {'registration': 'N727HB', 'maker': 'Lindstrand', 'volume_m3': 4250, 'max_passengers': 6, 'max_payload_kg': 600.0, 'hours_since_inspection': 12.0},
    {'registration': 'N88SKY', 'maker': 'Ultramagic', 'volume_m3': 2550, 'max_passengers': 2, 'max_payload_kg': 230.0, 'hours_since_inspection': 98.2},
    {'registration': 'N310UP', 'maker': 'Kubicek', 'volume_m3': 6000, 'max_passengers': 10, 'max_payload_kg': 950.0, 'hours_since_inspection': 33.7},
]


def flights_for(batch: str, start: dt.date, days: int, rng: random.Random) -> list[dict]:
    rows = []
    for d in range(days):
        day = start + dt.timedelta(days=d)
        for slot, hour in enumerate((6, 18)):  # dawn and evening flights
            if rng.random() < 0.25:
                continue  # weather hold
            env = rng.choice(ENVELOPES)
            n = rng.randint(1, env['max_passengers'])
            launch = dt.datetime(day.year, day.month, day.day, hour, rng.choice([5, 15, 30]), tzinfo=TZ)
            minutes = rng.randint(45, 95)
            burns = [{'t': f'{m:02d}:{rng.randint(0, 59):02d}', 'secs': round(rng.uniform(2, 9), 1)} for m in sorted(rng.sample(range(minutes), rng.randint(12, 30)))]
            manifest = [{'name': rng.choice(FIRST), 'kg': (round(rng.uniform(55, 105), 1) if rng.random() > 0.1 else None)} for _ in range(n)]
            rows.append({
                'flight_id': f'{day:%Y%m%d}-{"AM" if slot == 0 else "PM"}-{env["registration"]}',
                'registration': env['registration'],
                'pilot': rng.choice(PILOTS),
                'launch_site': rng.choice(SITES),
                'launch_at': launch.isoformat(),
                'landing_at': (launch + dt.timedelta(minutes=minutes)).isoformat(),
                'wind_kts': round(rng.uniform(1, 11), 1),
                'burner_log': burns,
                'manifest': manifest,
                'batch': batch,
            })
    return rows


def main() -> None:
    catalog_dir = os.environ.get('BALLOONS_DIR', 'balloons')  # or pxt://<org>:<db>/balloons
    TableModel.bind_all(catalog_dir)
    t = pxt.get_table(f'{catalog_dir}/envelopes')
    if t.count() == 0:
        t.insert(ENVELOPES)
    rng = random.Random(20261020)
    data = Path(__file__).parent / 'data'
    data.mkdir(exist_ok=True)
    start = dt.date(2026, 9, 1)
    for i in range(3):
        batch = f'batch_{i + 1:02d}'
        rows = flights_for(batch, start + dt.timedelta(days=10 * i), 10, rng)
        (data / f'{batch}.json').write_text(json.dumps(rows, indent=1))
        print(f'wrote data/{batch}.json ({len(rows)} flights)')
    print(f'envelopes: {t.count()}')


if __name__ == '__main__':
    main()
