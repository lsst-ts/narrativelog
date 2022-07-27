==========
Change Log
==========

0.4.0
-----

* Rename column ``date_user_specified`` to ``date_begin``.
* Add column ``date_end``.

0.3.0
-----

* Add columns ``systems``, ``subsystems``, and ``cscs``.

0.2.4
-----

* add_message: improve handling of the ``date_user_specified`` parameter.
  Document that it must not include time zone information, and raise a clear error if it does.

0.2.3
-----

* find_messages: improve validation of the ``order_by`` query parameter.
* Update to python 3.10.
* Modernize type annotations, applying changes that required Python 3.9 or 3.10.
  Use native types or `collections.abc` where possible.
  Replace `typing.Union` and `typing.Optional` with ``|``.
  Remove ``from __future__ import annotations`` where possible.

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
