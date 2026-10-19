"""Consistent SQLite backup / restore-to-NEW-file only. No source file is modified.
Run with Python; snapshot paths must be absolute, private, and outside application root.
Snapshots contain ALL account, session and salary data: protect/encrypt before off-host storage.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"auth_user", "operations_employee", "operations_assignment", "operations_auditevent", "django_migrations", "django_session", "login_throttle"}

def inspect(connection):
    if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise ValueError("SQLite integrity check failed")
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not REQUIRED.issubset(tables):
        raise ValueError("Not an initialized Powerline database: required tables missing")
    tracked = REQUIRED | ({"operations_enquiry", "operations_servicejob", "operations_technicianaccess", "operations_locationshare"} & tables)
    return {t: connection.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0] for t in sorted(tracked)}

def snapshot(source, target):
    source, target = Path(source), Path(target)
    if not source.is_absolute() or not target.is_absolute():
        raise ValueError("Use absolute source and destination paths")
    source = source.resolve(strict=True)
    parent = target.parent.resolve(strict=True)
    target = parent / target.name
    if not source.is_file():
        raise ValueError("Source must be a regular SQLite file")
    if parent.is_relative_to(ROOT.resolve()):
        raise ValueError("Destination must be outside application/source/static directories")
    mode = parent.stat().st_mode
    if mode & 0o077:
        raise ValueError("Destination directory must be private (mode 700 or stricter)")
    if source == target:
        raise ValueError("Source and destination must differ")
    # O_EXCL prevents overwrite and refuses symlinks, even for an empty existing file.
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=30) as src:
            inspect(src)
            with sqlite3.connect(target, timeout=30) as dst:
                src.backup(dst, pages=256, sleep=0.1)
                tables = {r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "operations_locationshare" in tables:
                    dst.execute("DELETE FROM operations_locationshare")
                    dst.commit()
                    dst.execute("VACUUM") # location samples must not survive in snapshot free pages
                counts = inspect(dst)
            # Counts can legitimately change during a live backup. The snapshot's own
            # integrity is checked; exact equality is checked by the quiescent rehearsal.
        with open(target, "rb") as f:
            os.fsync(f.fileno())
        return {"file": str(target), "integrity": "ok", "mode": oct(stat.S_IMODE(target.stat().st_mode)), "table_counts": counts}
    except BaseException:
        target.unlink(missing_ok=True)
        raise

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["backup", "restore-new"])
    p.add_argument("source"); p.add_argument("destination")
    args = p.parse_args()
    try:
        result = snapshot(args.source, args.destination)
    except (ValueError, OSError, sqlite3.Error) as e:
        p.exit(1, "No database replaced: " + str(e) + "\n")
    print(json.dumps({"operation": args.operation, **result}, indent=2))
if __name__ == "__main__": main()
