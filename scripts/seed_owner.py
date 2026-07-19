"""Idempotently bootstrap the deployment owner account for local dev.

Run from the backend directory (dev.sh does this automatically on every
start, not just --seed):

    cd backend && uv run python ../scripts/seed_owner.py

Upserts petr.pascenko@gmail.com (Petr Paščenko) with the Organizer role
and a fixed dev password. Combined with dev.sh's default
HEMA_SQUIRE_OWNER_EMAIL=petr.pascenko@gmail.com, the account is also the
deployment Owner (config-computed, never stored) — see design D7.

The password is a fixed, deliberately non-secret dev value; production
deployments set their own owner credentials via a real signup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from backend/ so `app` imports

EMAIL = "petr.pascenko@gmail.com"
DISPLAY_NAME = "Petr Paščenko"
PASSWORD = "swordismylife"


def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.auth import hash_password
    from app.db import engine
    from app.models import Fencer, Role

    with Session(engine) as session:
        fencer = session.scalar(select(Fencer).where(Fencer.email == EMAIL))
        if fencer is None:
            fencer = Fencer(email=EMAIL, display_name=DISPLAY_NAME)
            session.add(fencer)
        fencer.display_name = DISPLAY_NAME
        fencer.password_hash = hash_password(PASSWORD)
        fencer.role = Role.ORGANIZER
        session.commit()

    print(f"owner account ready: {EMAIL} / {PASSWORD} (Organizer role)")


if __name__ == "__main__":
    main()
