import threading

import pytest

from src import rooms
from src.rooms import CODE_ALPHABET, CODE_LENGTH, RoomStore

MOVIES = [
    {"title": "Dune", "year": 1984, "rating": 6.3},
    {"title": "Dune", "year": 2021, "rating": 8.0},
    {"title": "Up", "year": 2009, "rating": 8.3},
]


@pytest.fixture
def store():
    return RoomStore()


def test_code_format(store):
    code = store.create_room("Bat", MOVIES)
    assert len(code) == CODE_LENGTH
    assert all(ch in CODE_ALPHABET for ch in code)


def test_codes_are_unique(store):
    codes = {store.create_room("Bat", MOVIES) for _ in range(200)}
    assert len(codes) == 200


def test_empty_room_rejected(store):
    with pytest.raises(ValueError):
        store.create_room("Bat", [])


def test_join_is_case_insensitive(store):
    code = store.create_room("Bat", MOVIES)
    assert store.room_exists(code.lower())
    assert not store.room_exists("ZZZZZ")


def test_unknown_room_raises(store):
    with pytest.raises(KeyError):
        store.vote("NOPE", "Bat", 0)


def test_one_vote_per_person(store):
    code = store.create_room("Bat", MOVIES)
    store.vote(code, "Bat", 0)
    store.vote(code, "  BAT ", 2)          # same person, changed mind
    assert store.voter_count(code) == 1
    assert [count for _, count in store.results(code)] == [0, 0, 1]


def test_blank_name_rejected(store):
    code = store.create_room("Bat", MOVIES)
    with pytest.raises(ValueError):
        store.vote(code, "   ", 0)


def test_invalid_choice_rejected(store):
    code = store.create_room("Bat", MOVIES)
    with pytest.raises(ValueError):
        store.vote(code, "Bat", 3)
    with pytest.raises(ValueError):
        store.vote(code, "Bat", -1)


def test_same_title_movies_counted_separately(store):
    code = store.create_room("Bat", MOVIES)
    store.vote(code, "A", 0)
    store.vote(code, "B", 1)
    store.vote(code, "C", 1)
    assert store.winner(code)["year"] == 2021


def test_no_votes_no_winner(store):
    code = store.create_room("Bat", MOVIES)
    assert store.winner(code) is None


def test_tie_broken_by_rating(store):
    code = store.create_room("Bat", MOVIES)
    store.vote(code, "A", 1)   # Dune 2021, 8.0
    store.vote(code, "B", 2)   # Up, 8.3
    assert store.winner(code)["title"] == "Up"


def test_rooms_are_independent(store):
    a = store.create_room("A", MOVIES)
    b = store.create_room("B", MOVIES)
    store.vote(a, "X", 0)
    assert store.voter_count(b) == 0


def test_old_rooms_expire(store, monkeypatch):
    old = store.create_room("Bat", MOVIES)
    future = rooms.time.time() + rooms.ROOM_LIFETIME_SECONDS + 1
    monkeypatch.setattr(rooms.time, "time", lambda: future)
    store.create_room("New", MOVIES)       # creating a room cleans up old ones
    assert not store.room_exists(old)


def test_many_threads_voting_at_once(store):
    """100 people vote at the same moment - no vote may be lost."""
    code = store.create_room("Bat", MOVIES)
    threads = [threading.Thread(target=store.vote, args=(code, f"user{i}", i % 3))
               for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert store.voter_count(code) == 100
    assert sum(count for _, count in store.results(code)) == 100
