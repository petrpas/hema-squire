from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def apply_sqlite_pragmas(target: Engine) -> None:
    """Put a SQLite engine into the shape production needs, on every connection.

    A function rather than an inline listener so the test fixtures can build
    their engine the same way: pragmas that hold only in production are pragmas
    whose consequences are discovered in production. Non-SQLite engines are
    left alone, so this is a no-op after an eventual Postgres move.
    """
    if target.dialect.name != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _set_session_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        # Contending writers wait instead of failing. Python's driver already
        # applies a 5 s timeout of its own; stating it here makes the value part
        # of the schema's definition rather than a driver default.
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Matches the eventual Postgres target: a violation surfaces on the
        # write that causes it, not during a future migration.
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # WAL is Litestream's prerequisite — it replicates by reading the WAL. It is
    # a property of the database file rather than of a connection, so it is set
    # once, here, instead of on every connect: the switch needs an exclusive
    # lock, and SQLite returns "database is locked" for it immediately rather
    # than waiting out busy_timeout. Per-connection, that turns a moment of
    # write contention into connections that fail before serving anything.
    raw_connection = target.raw_connection()
    try:
        cursor = raw_connection.cursor()
        # PRAGMA runs outside a transaction on this driver, which the journal
        # switch requires.
        if cursor.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    finally:
        raw_connection.close()


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
apply_sqlite_pragmas(engine)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
