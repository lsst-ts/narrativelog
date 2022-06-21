#############
Narrative Log
#############

Narrative log is a REST web service to create and manage operator-generated log messages.
(See the exposure log service for operator-generated log messages associated with a particular exposure.)

The service runs at _address_:8080/narrativelog
and OpenAPI docs are available at _address_:8080/narrativelog/docs.

Messages are immutable, other than two fields: ``date_invalidated`` and ``is_valid``
(which is computed from ``date_invalidated``).
These fields provide a reasonable approximation of deletion and modification.

Configuration
-------------

The service is configured via the following environment variables;
All are optional except the few marked "(required)":

* ``NARRATIVELOG_DB_USER``: narrativelog database user name: default="narrativelog".
* ``NARRATIVELOG_DB_PASSWORD``: narrativelog database password; default="".
* ``NARRATIVELOG_DB_HOST``: narrativelog database server host; default="localhost".
* ``NARRATIVELOG_DB_PORT``: narrativelog database server port; default="5432".
* ``NARRATIVELOG_DB_DATABASE``: narrativelog database name; default="narrativelog".
* ``SITE_ID`` (required): Where this is deployed, e.g. "summit" or "base".

Developer Guide
---------------

Create (once) and activate a local conda environment::

  conda create --name square python=3.10
  conda env list

  conda activate square

For development work, you can install dependencies into the current conda environment,
and put the src directory in the PYTHONPATH using::

  make init
 
If you change requirements (in requirements/dev.in or main.in),
or if running the code gives a "package not found" error,
update the generated dependencies and install the new requirements using::

  make update

tox configuration goes in pyproject.toml (not tox.ini, as tox documentation often suggests).

To run tests (including code coverage, linting and typing)::

  tox

If that fails with a complaint about missing packages try rebuilding your environment::

  tox -r

To lint the code (run it twice if it reports a linting error the first time)::

  tox -e lint

To check type annotation with mypy::

  tox -e typing

To run the service, you will need a running Postgres server with a user named ``narrativelog``
that has permission to create tables and rows, and a database also named ``narrativelog``.
With the Postgres server running, for example::

  # Configure the service.
  export SITE_ID=test
  # Also set NARRATIVELOG_DB_x environment variables as needed; see Configuration above

  # Start the service.
  # The default port is 8000, but the LSST standard port is 8080.
  # --reload will reload the source code when you change it (don't use for production).
  uvicorn narrativelog.main:app [--port n] [--reload]

  # If running the service locally on port 8000, connect to it at: http://localhost:8000/narrativelog/

Postgres Guide
--------------

This is a very basic guide focused on the narrativelog service.

To start postgres manually (in case you don't routinely leave it running)::

    pg_ctl -D /usr/local/var/postgres start

To stop postgres manually::

    pg_ctl -D /usr/local/var/postgres stop -s -m fast

To connect to the postgres server in order to create a new user or database::

    psql -U postgres -d postgres

To create the narrativelog user and database::

    CREATE USER narrativelog WITH CREATEDB;
    CREATE DATABASE narrativelog;

To connect as user narrativelog and use the narrativelog database (e.g. to see data or schema)::

    psql -U narrativelog -d narrativelog

List all databases::

    \l

Show the schema for the current table::

    \d
