"""Balloon flight ops: the operator's command line over the Pixeltable flight log.

    python cli.py import data/batch_*.json     # idempotent: a file or flight seen before is skipped
    python cli.py logbook "R. Okafor"          # one pilot's flights, newest first
    python cli.py envelope N451BA              # flights, minutes and propane for one envelope
    python cli.py windy --min 8                # launches at or above 8 kt for the safety review
    python cli.py overweight                   # flights over the envelope's passenger or payload limit
    python cli.py fingerprint [--db URI]       # recompute the project fingerprint with the public helpers

Set BALLOONS_DIR to use another catalog directory (default: balloons). Point PIXELTABLE at a
Pixeltable Cloud database with `pxt schema update app.py pxt://<org>:<db>` and
BALLOONS_DIR=pxt://<org>:<db>.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.utils.project import digest, member_hash, pyproject_hash

ROOT = Path(__file__).resolve().parent
CATALOG = os.environ.get('BALLOONS_DIR', 'balloons')


def _tables():
    from app import TableModel

    TableModel.bind_all(CATALOG)
    return (pxt.get_table(f'{CATALOG}/envelopes'), pxt.get_table(f'{CATALOG}/flights'), pxt.get_table(f'{CATALOG}/imports'))


def file_hash(path: Path) -> str:
    """The hash a project fingerprint records for this file (member_hash over its SHA-256)."""
    if path.is_symlink():  # a symlink is identified by the path it stores, not by its target's bytes
        return member_hash(digest(os.readlink(path)), symlink=True)
    if path.name == 'pyproject.toml':
        return member_hash(pyproject_hash(path.read_bytes()), symlink=False)
    return member_hash(hashlib.sha256(path.read_bytes()).hexdigest(), symlink=False)


def _parse(row: dict) -> dict:
    row = dict(row)
    for k in ('launch_at', 'landing_at'):
        row[k] = dt.datetime.fromisoformat(row[k])
    return row


def cmd_import(args) -> int:
    _, flights, imports = _tables()
    seen_files = {r['file_hash'] for r in imports.select(imports.file_hash).collect()}
    known = {r['flight_id']: r['record_digest'] for r in flights.select(flights.flight_id, flights.record_digest).collect()}
    total = 0
    for name in args.files:
        path = Path(name)
        fh = file_hash(path)
        if fh in seen_files and not args.force:
            print(f'{path.name}: already imported (file hash {fh[:12]}), skipped')
            continue
        rows = [_parse(r) for r in json.loads(path.read_text())]
        new = [r for r in rows if r['flight_id'] not in known]
        dupes = len(rows) - len(new)
        if new:
            status = flights.insert(new, on_error='abort')
            print(f'{path.name}: {status.num_rows} flights inserted, {dupes} already in the log')
        else:
            print(f'{path.name}: 0 new flights, {dupes} already in the log')
        imports.insert([{'file_hash': fh, 'file_name': path.name, 'flights': len(new), 'imported_at': dt.datetime.now(dt.timezone.utc)}], on_error='abort') if fh not in seen_files else None
        seen_files.add(fh)
        known.update({r['flight_id']: None for r in new})
        total += len(new)
    print(f'total new flights: {total}; log now holds {flights.count()} flights')
    return 0


def _print(rows) -> None:
    for r in rows:
        print('  ' + ' | '.join(str(round(v, 1) if isinstance(v, float) else v) for v in r.values()))


def cmd_logbook(args) -> int:
    _, f, _ = _tables()
    rows = list(
        f.where(f.pilot == args.pilot)
        .order_by(f.launch_at, asc=False)
        .select(f.flight_id, f.registration, f.launch_site, f.launch_at, f.minutes, f.wind)
        .collect()
    )
    print(f'{args.pilot}: {len(rows)} flights')
    _print(rows[: args.n])
    return 0


def cmd_envelope(args) -> int:
    _, f, _ = _tables()
    _print(
        f.where(f.registration == args.registration)
        .group_by(f.registration)
        .select(f.registration, flights=pxtf.count(f.flight_id), minutes=pxtf.sum(f.minutes), propane_kg=pxtf.sum(f.propane_kg))
        .collect()
    )
    return 0


def cmd_windy(args) -> int:
    _, f, _ = _tables()
    rows = list(
        f.where(f.wind_kts >= args.min)
        .order_by(f.wind_kts, asc=False)
        .select(f.flight_id, f.pilot, f.launch_site, f.wind_kts, f.wind)
        .collect()
    )
    print(f'{len(rows)} launches at or above {args.min} kt')
    _print(rows)
    return 0


def cmd_overweight(args) -> int:
    envelopes, flights, _ = _tables()
    limits = {r['registration']: r for r in envelopes.collect()}
    bad = 0
    for r in flights.select(flights.flight_id, flights.registration, flights.manifest, flights.payload).collect():
        env = limits[r['registration']]
        n = len(r['manifest'])
        if n > env['max_passengers'] or r['payload'] > env['max_payload_kg']:
            bad += 1
            print(f"  {r['flight_id']}: {n} pax / {r['payload']} kg (limit {env['max_passengers']} pax / {env['max_payload_kg']} kg)")
    print(f'{bad} flights over limits')
    return 1 if bad else 0


def cmd_fingerprint(args) -> int:
    """Recompute the archive part of the project fingerprint from the file bytes and compare with pxt's own."""
    from pixeltable import catalog
    from pixeltable.config import Config
    from pixeltable.utils.project import project_fingerprint

    cfg = Config.get()
    if args.db:
        db_config = cfg.get_database_config(catalog.Path.parse(args.db, allow_empty_path=True))
    else:  # the local database entry (no name in pixeltable.toml)
        db_config = next((d for d in cfg.get_value('database', list) or [] if d.name == 'local'), None)
    # db_config's exclude list decides which project files are fingerprinted (and uploaded to the cloud)
    fp = project_fingerprint(cfg.project_root, db_config)
    mine = {rel: file_hash(cfg.project_root / rel) for rel in fp.files}
    mismatched = sorted(rel for rel in fp.files if fp.files[rel] != mine[rel])
    out = {
        'project_root': '.',
        'target': args.db or 'local',
        'files': len(mine),
        'archive_digest': digest(mine),
        'archive_digest_pxt': fp.archive_digest(),
        'matches_pxt': not mismatched and digest(mine) == fp.archive_digest(),
        'mismatched': mismatched,
        'pixeltable_version': fp.pixeltable_version,
    }
    if args.db:
        res = subprocess.run(['pxt', 'db', 'diff', args.db, '--json'], capture_output=True, text=True, cwd=ROOT)
        try:
            out['db_diff'] = json.loads(res.stdout)
        except json.JSONDecodeError:
            out['db_diff'] = {'exit': res.returncode, 'stderr': res.stderr.strip()[-400:]}
    if args.json:
        print(json.dumps(out, indent=1, default=str))
    else:
        for k, v in out.items():
            if k != 'db_diff':
                print(f'{k}: {v}')
        for rel in sorted(mine):
            print(f'  {mine[rel][:12]}  {rel}')
    return 0 if out['matches_pxt'] else 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='cli.py', description='Hot-air balloon flight ops over a Pixeltable flight log')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('import', help='import flight batch files (JSON lists of flights)')
    s.add_argument('files', nargs='+')
    s.add_argument('--force', action='store_true', help='re-read a file whose hash was imported before')
    s.set_defaults(fn=cmd_import)
    s = sub.add_parser('logbook', help="one pilot's flights")
    s.add_argument('pilot')
    s.add_argument('-n', type=int, default=10)
    s.set_defaults(fn=cmd_logbook)
    s = sub.add_parser('envelope', help='totals for one envelope')
    s.add_argument('registration')
    s.set_defaults(fn=cmd_envelope)
    s = sub.add_parser('windy', help='launches at or above a wind speed')
    s.add_argument('--min', type=float, default=8.0)
    s.set_defaults(fn=cmd_windy)
    s = sub.add_parser('overweight', help='flights over passenger or payload limits (exit 1 if any)')
    s.set_defaults(fn=cmd_overweight)
    s = sub.add_parser('fingerprint', help='recompute the project fingerprint with digest/member_hash/pyproject_hash')
    s.add_argument('--db', help='a Pixeltable Cloud database, pxt://<org>:<db>; also runs `pxt db diff --json`')
    s.add_argument('--json', action='store_true')
    s.set_defaults(fn=cmd_fingerprint)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
