=============
Release Notes
=============

0.2.2
-----

* Improve alembic migration to handle the case that the message table does not exist.
* Add ``tests/test_alembic_migration.py``.
* `LogMessageDatabase`: add message_table constructor argument to improve encapsulation.
* setup.cfg: specify asyncio_mode = auto.

0.2.1
-----

* Dockerfile: switch to a simpler base image, as per current SQuaRE recommendations.
* Add scripts/start-api.sh to run schema evolution and start the service.

0.2.0
-----

* Add support for schema evolution using alembic.
* Add min_level and max_level arguments to find_messages.

0.1.0
-----

* First release
