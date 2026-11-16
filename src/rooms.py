"""Voting rooms, stored in plain Python objects.

The app keeps ONE RoomStore for the whole server (via st.cache_resource),
so every phone connected to the same server sees the same rooms.

Several people can vote at the same instant, and Streamlit runs each
browser session in its own thread. Without a lock, two threads could
change the same dict at once and a vote could be lost. So every method
that reads or changes rooms does it while holding `self._lock`.
"""

import random
import string
import threading
import time

# No 0/O or 1/I, so codes are easy to read out loud.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits
                        if c not in "0O1I")
CODE_LENGTH = 4
ROOM_LIFETIME_SECONDS = 6 * 60 * 60   # forget rooms after 6 hours


class Room:
    """One movie-night vote.

    candidates: list of dicts like {"title": ..., "year": ..., "rating": ...}
    votes:      {voter_key: index into candidates}
    Votes store the candidate INDEX, not the title, because two different
    movies can share a title (e.g. "Dune" 1984 and "Dune" 2021).
    """

    def __init__(self, code, host, candidates):
        self.code = code
        self.host = host
        self.candidates = candidates
        self.votes = {}
        self.created_at = time.time()


def normalize_name(name):
    """'  Bat ' and 'bat' count as the same voter."""
    return " ".join(name.split()).lower()


class RoomStore:
    """All rooms on this server, safe to use from many threads."""

    def __init__(self, rng=None):
        self._rooms = {}
        self._lock = threading.Lock()
        self._rng = rng or random.SystemRandom()

    def _new_code(self):
        """Make a code that is not already in use (caller holds the lock)."""
        while True:
            code = "".join(self._rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                return code

    def _remove_old_rooms(self, now):
        """Drop expired rooms so memory doesn't grow forever (caller holds lock)."""
        for code in list(self._rooms):
            if now - self._rooms[code].created_at > ROOM_LIFETIME_SECONDS:
                del self._rooms[code]

    def create_room(self, host, candidates):
        """Open a new room and return its code."""
        if not candidates:
            raise ValueError("A room needs at least one movie to vote on.")
        with self._lock:
            self._remove_old_rooms(time.time())
            code = self._new_code()
            self._rooms[code] = Room(code, host, list(candidates))
            return code

    def room_exists(self, code):
        with self._lock:
            return code.strip().upper() in self._rooms

    def get_candidates(self, code):
        """Return a copy of the room's movie list (raises KeyError if no room)."""
        with self._lock:
            return list(self._rooms[code.strip().upper()].candidates)

    def vote(self, code, voter_name, choice):
        """Record a vote. Voting again REPLACES your earlier vote.

        That is how "one vote per person" is enforced: the vote dict is
        keyed by the voter's normalised name, so a name can only appear once.
        """
        key = normalize_name(voter_name)
        if not key:
            raise ValueError("Please enter your name before voting.")
        with self._lock:
            room = self._rooms[code.strip().upper()]
            if not 0 <= choice < len(room.candidates):
                raise ValueError("That movie is not in this room.")
            room.votes[key] = choice

    def results(self, code):
        """Return [(candidate, vote_count), ...] in the original order."""
        with self._lock:
            room = self._rooms[code.strip().upper()]
            counts = [0] * len(room.candidates)
            for choice in room.votes.values():
                counts[choice] += 1
            return list(zip(room.candidates, counts))

    def voter_count(self, code):
        with self._lock:
            return len(self._rooms[code.strip().upper()].votes)

    def winner(self, code):
        """Return the winning candidate, or None if nobody voted yet.

        Ties are broken by higher IMDb rating, then by title A-Z,
        so the answer is always the same for the same votes.
        """
        tally = self.results(code)
        voted = [(movie, count) for movie, count in tally if count > 0]
        if not voted:
            return None
        best = min(voted, key=lambda pair: (-pair[1], -pair[0]["rating"], pair[0]["title"]))
        return best[0]
