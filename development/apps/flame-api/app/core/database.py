from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import Settings


class Base(DeclarativeBase):
    """Metadata for FLAME-owned tables in the dedicated schema."""

    metadata = MetaData(
        schema="flame",
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )


class Database:
    """Own engine lifecycle only. Feature repositories own their queries."""

    def __init__(self, settings: Settings):
        self.engine = None
        self.sessions = None
        if settings.database_url:
            self.engine = create_engine(
                settings.database_url.get_secret_value(),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                pool_timeout=5,
                connect_args={"connect_timeout": settings.database_connect_timeout},
            )
            self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def ready(self) -> bool:
        if self.engine is None:
            return False
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            # Do not leak DSNs or driver exception details.
            return False

    def session(self) -> Session:
        if self.sessions is None:
            raise RuntimeError("Database is not configured")
        return self.sessions()

    def close(self):
        if self.engine is not None:
            self.engine.dispose()
