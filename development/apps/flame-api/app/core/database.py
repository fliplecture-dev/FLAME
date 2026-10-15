from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool
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
            url = make_url(settings.database_url.get_secret_value())
            supabase_pooler = bool(url.host and url.host.endswith(".pooler.supabase.com"))
            transaction_pooler = supabase_pooler and url.port == 6543
            connect_args = {"connect_timeout": settings.database_connect_timeout}
            if transaction_pooler:
                # Transaction pooling cannot preserve prepared statements.
                connect_args["prepare_threshold"] = None
            # Warm serverless instances must not each reserve their own idle
            # sessions in Supabase's shared, bounded pool.
            pool_options = ({"poolclass": NullPool}
                            if transaction_pooler or (supabase_pooler and settings.environment == "production")
                            else {"pool_size": 5, "max_overflow": 5, "pool_timeout": 5})
            self.engine = create_engine(
                url,
                pool_pre_ping=True,
                **pool_options,
                connect_args=connect_args,
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
