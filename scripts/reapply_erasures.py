#!/usr/bin/env python
"""Erase again, in a restored database, every record the latest replica says
was erased (spec account-deletion, A restore reapplies erasures; design D8).

    python scripts/reapply_erasures.py LATEST.sqlite

`LATEST.sqlite` is the newest state of the replica, restored without a
timestamp; the database to repair is the application's own, named by
HEMA_SQUIRE_DATABASE_URL as everywhere else. Run it after migrating that
database and before the service opens: a restore to last week would otherwise
bring back whoever was deleted since. `deploy/restore.sh` does exactly that.

The log is read with the standard library, so a latest state that predates the
log simply has nothing to apply. Idempotent: running it twice changes nothing
the second time."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from backend/ (or /app in the image)


def read_log(latest: Path) -> list[tuple[int, str]]:
    with sqlite3.connect(f"file:{latest}?mode=ro", uri=True) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
        if "account_erasures" not in tables:
            return []
        return [
            (int(fencer_id), str(kind))
            for fencer_id, kind in connection.execute(
                "select fencer_id, kind from account_erasures order by id"
            )
        ]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    from sqlalchemy.orm import Session

    from app.account_deletion import reapply
    from app.db import engine

    log = read_log(Path(sys.argv[1]))
    with Session(engine) as session:
        changed = reapply(session, log)
        session.commit()
    print(f"{len(log)} erasures in the log, {changed} applied again")


if __name__ == "__main__":
    main()
