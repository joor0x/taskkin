import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.assignments.models import TaskAssignment  # noqa: F401
from app.audit.models import AuditEvent  # noqa: F401

# Import all models to register them on Base.metadata
from app.auth.models import RefreshToken, User  # noqa: F401
from app.common.models import IdempotencyKey  # noqa: F401

# Import settings and Base
from app.config import settings
from app.evidence.models import Evidence  # noqa: F401
from app.infrastructure.database import Base
from app.organizations.models import (  # noqa: F401
    APIKey,
    Organization,
    OrganizationMember,
)
from app.payments.models import LedgerEntry, Wallet  # noqa: F401
from app.reputation.models import ReputationEvent  # noqa: F401
from app.submissions.models import Submission  # noqa: F401
from app.tasks.models import Task  # noqa: F401
from app.webhooks.models import WebhookDelivery, WebhookEndpoint  # noqa: F401
from app.workers.models import WorkerProfile  # noqa: F401

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging. This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Set database URL dynamically from environment/settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
