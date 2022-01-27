############
Exposure Log
############

Narrative log is a REST web service to create and manage log messages that are associated with a particular exposure.

The service runs at _address_:8080/narrativelog
and OpenAPI docs are available at _address_:8080/narrativelog/docs.

Messages are immutable, other than two fields: ``date_invalidated`` and ``is_valid``
(which is computed from ``date_invalidated``).
These fields provide a reasonable approximation of deletion and modification.

Configuration
-------------

The service is configured via the following environment variables;
All are optional except the few marked "(required)":

* ``BUTLER_URI_1`` (required): URI to an butler data repository, which is only read.
  Note that Exposure Log only reads the registry, so the actual data files are optional.
* ``BUTLER_URI_2``: URI to a second, optional, data repository, which is searched after the first one.
* ``narrativelog_DB_USER``: narrativelog database user name: default="narrativelog".
* ``narrativelog_DB_PASSWORD``: narrativelog database password; default="".
* ``narrativelog_DB_HOST``: narrativelog database server host; default="localhost".
* ``narrativelog_DB_PORT``: narrativelog database server port; default="5432".
* ``narrativelog_DB_DATABASE``: narrativelog database name; default="narrativelog".
* ``SITE_ID`` (required): Where this is deployed, e.g. "summit" or "base".

Developer Guide
---------------

Create (once) and activate a local conda environment::

  conda create --name square python=3.8
  conda env list

  conda activate square

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

To run the service, first set the configuration environment variables, then::

  uvicorn narrativelog.main:app --port n

To run the service locally, you will need a running Postgres server
with a user named ``narrativelog`` that has permission to create tables and rows,
and a database also named ``narrativelog``.
With the Postgres server running::

  export SITE_ID=test
  export BUTLER_URI_1=/Users/rowen/UW/LSST/tsrepos/narrativelog/tests/data/hsc_raw
  # Also set narrativelog_DB_x environment variables as needed; see above

  uvicorn narrativelog.main:app --reload

  # Then open this link in a browser: http://localhost:8000/narrativelog/
  # For documentation open http://localhost:8000/narrativelog/docs

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
