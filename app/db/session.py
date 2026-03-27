from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)

    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "leads" not in inspector.get_table_names():
        return

    lead_columns = {column["name"] for column in inspector.get_columns("leads")}
    if "customer_id" in lead_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO customers (name, phone, email, address)
                SELECT name, phone, email, address
                FROM leads
                """
            )
        )
        connection.execute(
            text(
                """
                ALTER TABLE leads
                ADD COLUMN customer_id INTEGER REFERENCES customers(id)
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE leads
                SET customer_id = (
                    SELECT customers.id
                    FROM customers
                    WHERE customers.phone = leads.phone
                    AND (
                        customers.email = leads.email
                        OR (customers.email IS NULL AND leads.email IS NULL)
                    )
                    LIMIT 1
                )
                """
            )
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
