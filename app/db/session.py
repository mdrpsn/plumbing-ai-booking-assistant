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
        _ensure_messages_have_conversation_id(inspector)
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

    inspector = inspect(engine)
    _ensure_messages_have_conversation_id(inspector)


def _ensure_messages_have_conversation_id(inspector) -> None:
    if "messages" not in inspector.get_table_names():
        return

    message_columns = {column["name"] for column in inspector.get_columns("messages")}
    if "conversation_id" in message_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE messages
                ADD COLUMN conversation_id INTEGER REFERENCES conversations(id)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO conversations (
                    customer_id,
                    lead_id,
                    channel,
                    status,
                    last_message_direction,
                    last_message_at
                )
                SELECT
                    messages.customer_id,
                    messages.lead_id,
                    messages.channel,
                    CASE
                        WHEN messages.direction = 'inbound' THEN 'customer_replied'
                        ELSE 'open'
                    END,
                    messages.direction,
                    messages.created_at
                FROM messages
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM conversations
                    WHERE conversations.customer_id = messages.customer_id
                    AND (
                        conversations.lead_id = messages.lead_id
                        OR (conversations.lead_id IS NULL AND messages.lead_id IS NULL)
                    )
                    AND conversations.channel = messages.channel
                )
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE messages
                SET conversation_id = (
                    SELECT conversations.id
                    FROM conversations
                    WHERE conversations.customer_id = messages.customer_id
                    AND (
                        conversations.lead_id = messages.lead_id
                        OR (conversations.lead_id IS NULL AND messages.lead_id IS NULL)
                    )
                    AND conversations.channel = messages.channel
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
