"""One-shot report: published, non-cancelled tournaments with no bank
account recorded (design fix-payment-instructions-visibility, Decision 4).

Run once after deploying that change, from the backend directory:

    cd backend && uv run python ../scripts/report_missing_bank_accounts.py

The bank account became a mandatory Setup item at that point, but the
publish gate only guards future transitions — a tournament already
published before then can be missing it and stay published, quietly
leaving its fencers unable to pay. There is no automatic repair: a bank
account cannot be invented. Fixing one is a manual Setup edit, on the
PAYMENTS tab. This script only lists which tournaments need it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))  # run from backend/ so `app` imports


def main() -> None:
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from app.db import engine
    from app.models import Registration, RegistrationState, Tournament

    with Session(engine) as session:
        tournaments = session.scalars(
            select(Tournament)
            .where(Tournament.published_at.is_not(None))
            .where(Tournament.cancelled_at.is_(None))
            .where((Tournament.bank_account.is_(None)) | (Tournament.bank_account == ""))
            .order_by(Tournament.date)
        ).all()

        if not tournaments:
            print("no published tournament is missing a bank account")
            return

        print(f"{len(tournaments)} published tournament(s) missing a bank account:\n")
        for tournament in tournaments:
            live = session.scalar(
                select(func.count())
                .select_from(Registration)
                .where(Registration.tournament_id == tournament.id)
                .where(
                    Registration.state.in_(
                        [RegistrationState.RESERVED, RegistrationState.PAID]
                    )
                )
            )
            print(
                f"  {tournament.slug:30} {tournament.display_name:30} "
                f"{tournament.date}  {live} live registration(s)"
            )


if __name__ == "__main__":
    main()
