__all__ = ["TAG_DESCRIPTION", "normalize_tags"]

import collections.abc
import http
import re

import fastapi

TAG_DESCRIPTION = (
    "Each tag must be at least two characters long, must start with a "
    "letter, and must contain only ASCII letters, digits, and "
    "_ (underscore). Tags are transformed to lowercase."
)

VALID_TAG_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]+$")


def normalize_tags(tags: collections.abc.Iterable[str]) -> list[str]:
    """Normalize a list of tags.

    Check the tags and, if all are valid, cast to lowercase.

    Parameters
    ----------
    tags
        Tags to normalize

    Returns
    -------
    normalized_tags
        Normalized tags, in the original order.

    Raises
    ------
    fastapi.HTTPException
        with status_code = http.HTTPStatus.BAD_REQUEST
        if any of the tags are invalid.
    """
    bad_tags = [tag for tag in tags if VALID_TAG_RE.match(tag) is None]
    if bad_tags:
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail=f"Invalid tags: {sorted(bad_tags)}",
        )
    return [tag.lower() for tag in tags]
