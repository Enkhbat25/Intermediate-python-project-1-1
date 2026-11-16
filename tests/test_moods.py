import pytest

from src.moods import MOOD_TO_GENRES, genres_for_mood


def test_any_mood_has_no_restriction():
    assert genres_for_mood("Any mood") == []


def test_scare_me_is_horror():
    assert genres_for_mood("Scare me") == ["Horror"]


def test_unknown_mood_raises():
    with pytest.raises(KeyError):
        genres_for_mood("Hungry")


def test_returned_list_is_a_copy():
    genres_for_mood("Romantic").append("Horror")
    assert MOOD_TO_GENRES["Romantic"] == ["Romance"]
