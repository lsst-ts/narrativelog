import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, inspect, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from narrativelog.shared_state import create_db_url

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option("sqlalchemy.url", create_db_url())

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def do_run_migrations(connection):
    """Run a migration given an async connection.

    A helper function used by run_migrations_online.
    """
    log = logging.getLogger("alembic.script")
    log.setLevel(logging.INFO)
    context.configure(connection=connection, target_metadata=target_metadata)

    # This must be done after configuring the context,
    # else the migration does nothing.
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())

    with context.begin_transaction():
        context.run_migrations(log=log, table_names=table_names)


async def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    raise NotImplementedError("Not supported")
else:
    asyncio.run(run_migrations_online())
