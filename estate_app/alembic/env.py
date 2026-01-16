import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from core.settings import settings
from core.get_db import Base
from models.models import (
    User,
    SaleConversation,
    RentalConversation,
    SaleEncryptedMessage,
    RentalEncryptedMessage,
    BlacklistedToken,
    SaleListing,
    SaleListingImage,
    RentalListing,
    RentalListingImage,
    Tenant,
    Property,
    PropertyImage,
    UserProfile,
    LocalGovernmentArea,
    State,
)


from geoalchemy2 import Geography, Geometry
from geoalchemy2 import alembic_helpers
from core.settings import settings


config = context.config


config.set_main_option("sqlalchemy.url", settings.RENDER_DATABASE_URL)


fileConfig(config.config_file_name)


target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    return type_ != "schema"


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    DATABASE_URL = config.get_main_option("sqlalchemy.url")

    connectable = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        print("PostGIS extension enabled (or already exists).")

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
