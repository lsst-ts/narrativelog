import itertools

import fastapi
import pytest

from narrativelog.routers.normalize_tags import normalize_tags


def test_normalize_tags() -> None:
    good_short_tags = [
        valid_first_char + valid_second_char
        for valid_first_char, valid_second_char in itertools.product(
            ("a", "z", "A", "Z"),
            ("a", "z", "A", "Z", "0", "9", "_"),
        )
    ]

    normalized_tags = normalize_tags(good_short_tags)
    assert normalized_tags == [tag.lower() for tag in good_short_tags]

    good_arbitrary_tags = [
        "some_tag",
        "tag52",
        "a_tag",
        "a_long_tag_0123456789_" * 100,
    ]
    normalized_tags = normalize_tags(good_arbitrary_tags)
    assert normalized_tags == [tag.lower() for tag in good_arbitrary_tags]

    bad_tags = [
        "a",
        "z",
        "A",
        "Z",
        "0a",
        "9z",
        "_a",
        "a-b",
        "a b",
        "a,b",
        "a=b",
        "a?b",
        "aå",
    ]
    for bad_tag in bad_tags:
        with pytest.raises(fastapi.HTTPException):
            normalize_tags([bad_tag])
