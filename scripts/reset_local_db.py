#!/usr/bin/env python
"""Start the local database over, keeping the accounts and the tournament setup.

A development database fills with imported tables, parse decisions, rules and
row numbers that are tedious to clean and easy to leave in a confusing state.
This throws all of that away and puts back only what is annoying to retype: the
accounts that can log in, and each tournament's configuration — its mode, its
disciplines, the items it lends, its organizers.

    ./scripts/reset_local_db.py --dry-run    # dump and report, touch nothing
    ./scripts/reset_local_db.py              # dump, back up, recreate, reload

Run it from anywhere. The project's dependencies live in `backend/.venv` under
uv, not in whatever environment happens to be active, so the script re-runs
itself through `uv run` when it finds it cannot import them.

Why a column-level dump rather than the canonical JSON export: the export in
`app/export_json.py` is a *portable* document, and deliberately drops what does
not travel between deployments — the mode flags, the payment mode, the seating
deadline, the logo, the Fio token, the HR category map. Those are exactly the
settings this script exists to preserve. Here both ends are the same schema on
the same machine, so a faithful row copy is both simpler and lossless.

What is kept: fencers (with their password hashes, so logins still work),
tournaments, disciplines, extra items, organizer links.

What is dropped: registrations, import batches and their rows, parse/match/merge
decisions, manual rows, rules and their journal, row numbers, operations, bank
transactions, teams, HR snapshots. The fighters index is dropped too and
repopulates itself on the next start.

The database is never deleted outright — it is renamed aside with a timestamp,
and the dump is written next to it. Both are gitignored.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import decimal
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# the tables carried across, in the order they must be written: a tournament
# names its owner, a discipline names its tournament
KEPT = ["Fencer", "Tournament", "Discipline", "ExtraItem", "TournamentOrganizer"]

# set on the child when this script re-runs itself, so a missing module there is
# reported rather than causing another re-exec
_REEXEC = "HEMA_SQUIRE_RESET_REEXEC"


def reexec_under_uv() -> None:
    """Re-run this script through `uv run` when the app's imports are missing.

    The dependencies are `backend/.venv`, managed by uv — the same environment
    `dev.sh` runs the server in. A shell with the repository's own virtualenv
    active, or none at all, cannot import sqlalchemy, and the script would fail
    on its first app import with nothing done. Cheaper to relaunch correctly
    than to make the caller remember `cd backend && uv run`.
    """
    if os.environ.get(_REEXEC) == "1":
        return
    try:
        import sqlalchemy  # noqa: F401
    except ModuleNotFoundError:
        pass
    else:
        return
    try:
        result = subprocess.run(
            ["uv", "run", "python", str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=BACKEND,
            env={**os.environ, _REEXEC: "1"},
        )
    except FileNotFoundError:
        print(
            "this needs the backend environment, and uv is not installed.\n"
            "Install uv (https://docs.astral.sh/uv/) or run it yourself:\n"
            "  cd backend && uv run python ../scripts/reset_local_db.py",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    raise SystemExit(result.returncode)


def _plain(value):
    """A column value as JSON, in a form `_revive` can turn back."""
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode()}
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return {"__iso__": value.isoformat(), "__kind__": type(value).__name__}
    if isinstance(value, decimal.Decimal):
        return {"__decimal__": str(value)}
    return value


def _revive(value):
    if isinstance(value, dict):
        if "__bytes__" in value:
            return base64.b64decode(value["__bytes__"])
        if "__decimal__" in value:
            return decimal.Decimal(value["__decimal__"])
        if "__iso__" in value:
            kind = value["__kind__"]
            raw = value["__iso__"]
            if kind == "datetime":
                return datetime.datetime.fromisoformat(raw)
            if kind == "date":
                return datetime.date.fromisoformat(raw)
            return datetime.time.fromisoformat(raw)
    return value


def dump(session, models) -> dict:
    """Every row of the kept tables, ids and all.

    Ids travel because the database they land in is empty, and keeping them
    means the foreign keys between these tables need no remapping."""
    document = {"dumped_at": datetime.datetime.now().astimezone().isoformat(), "tables": {}}
    for name in KEPT:
        model = models[name]
        columns = [c.name for c in model.__table__.columns]
        rows = session.query(model).order_by(model.id).all()
        document["tables"][name] = [
            {column: _plain(getattr(row, column)) for column in columns} for row in rows
        ]
    return document


def load(session, models, document: dict) -> None:
    for name in KEPT:
        model = models[name]
        for record in document["tables"].get(name, []):
            session.add(model(**{k: _revive(v) for k, v in record.items()}))
        session.flush()
    session.commit()


def holders(database: Path) -> list[str]:
    """Processes with the database file open.

    Replacing a file a running server holds does not stop that server: its
    connections keep pointing at the old inode, so everything it writes goes to
    a file nothing will read again while the new database silently diverges.
    Worth refusing rather than discovering later.

    This process does not count. It has the database open itself — it just
    dumped from it — and so does the shell that re-executed it."""
    try:
        found = subprocess.run(
            ["lsof", "-t", "--", str(database)], capture_output=True, text=True, timeout=10
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []  # no lsof: fall through and trust the caller
    ours = {str(os.getpid()), str(os.getppid())}
    return [pid for pid in found.stdout.split() if pid.strip() and pid not in ours]


def counts(document: dict) -> str:
    return ", ".join(f"{len(rows)} {name}" for name, rows in document["tables"].items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write the dump and report what would happen; leave the database alone",
    )
    parser.add_argument(
        "--dump",
        type=Path,
        help="where to write the dump (default: beside the database)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the database even while a process holds it open (it will not notice)",
    )
    parser.add_argument(
        "--from-dump",
        type=Path,
        help="skip the dump and reload this file instead — for a second attempt",
    )
    args = parser.parse_args()

    reexec_under_uv()

    os.environ.setdefault("HEMA_SQUIRE_DEBUG", "1")
    # nothing may run against the database while it is being replaced
    os.environ["HEMA_SQUIRE_SCHEDULER_ENABLED"] = "false"
    os.environ["HEMA_SQUIRE_HR_AUTO_REFRESH"] = "false"
    os.environ["HEMA_SQUIRE_OPERATIONS_SWEEP_ENABLED"] = "false"

    from sqlalchemy.orm import Session

    from app import models as model_module
    from app.config import settings
    from app.db import engine

    url = settings.database_url
    if not url.startswith("sqlite"):
        print(f"refusing to run against a non-SQLite database: {url}", file=sys.stderr)
        return 2
    database = Path(url.split("sqlite:///")[-1])
    if not database.is_absolute():
        database = (BACKEND / database).resolve()

    models = {name: getattr(model_module, name) for name in KEPT}
    dump_path = args.dump or database.with_suffix(".reset-dump.json")

    if args.from_dump:
        document = json.loads(args.from_dump.read_text())
        print(f"reloading {args.from_dump}: {counts(document)}")
    else:
        if not database.exists():
            print(f"no database at {database}", file=sys.stderr)
            return 2
        with Session(engine) as session:
            document = dump(session, models)
        dump_path.write_text(json.dumps(document, ensure_ascii=False, indent=2))
        print(f"dumped {counts(document)}")
        print(f"  -> {dump_path}")

    if args.dry_run:
        print("\ndry run: the database was not touched.")
        return 0

    # close our own connections before asking who holds the file, so the dump
    # this script just took is not mistaken for a running server
    engine.dispose()
    open_by = holders(database)
    if open_by and not args.force:
        print(
            f"\n{database.name} is open by process {', '.join(open_by)} — the dev server.\n"
            "Stop it first (the running server would keep writing to the old file,\n"
            "which this script moves aside), then run this again. The dump is\n"
            f"already written, so the second run can skip straight to it:\n"
            f"  ./scripts/reset_local_db.py --from-dump {dump_path}",
            file=sys.stderr,
        )
        return 3

    if not args.from_dump:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = database.with_name(f"{database.name}.bak-{stamp}")
        shutil.move(database, backup)
        # WAL and shared-memory files belong to the database that was moved;
        # left behind, SQLite would read them against the new file
        for suffix in ("-wal", "-shm"):
            stray = database.with_name(database.name + suffix)
            if stray.exists():
                stray.unlink()
        print(f"backed up the old database -> {backup}")

    migrate = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    if migrate.returncode != 0:
        print(migrate.stdout + migrate.stderr, file=sys.stderr)
        print("\nmigration failed; the dump is kept and the backup is beside it.", file=sys.stderr)
        return 1
    print("created a fresh database at head")

    # the engine reconnects lazily after dispose(), so it now opens the file
    # alembic has just created
    with Session(engine) as session:
        load(session, models, document)
    print(f"reloaded {counts(document)}")
    print("\nthe fencer tables are empty; the accounts and the setup are as they were.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
