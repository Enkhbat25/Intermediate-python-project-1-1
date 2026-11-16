"""Moods are just friendly names for a group of IMDb genres."""

# Each mood maps to the IMDb genres that fit it.
# A movie fits a mood if it has AT LEAST ONE of these genres.
MOOD_TO_GENRES = {
    "Any mood": [],
    "Feel-good": ["Comedy", "Family", "Animation", "Music", "Musical"],
    "Romantic": ["Romance"],
    "Edge of my seat": ["Thriller", "Mystery", "Crime"],
    "Scare me": ["Horror"],
    "Pump me up": ["Action", "Adventure", "Sport", "War"],
    "Mind-bending": ["Sci-Fi", "Fantasy", "Mystery"],
    "Make me think": ["Drama", "Biography", "History", "Documentary"],
}


def genres_for_mood(mood):
    """Return the list of genres for a mood ([] means "no restriction").

    Raises KeyError for an unknown mood, so typos fail loudly in tests.
    """
    return list(MOOD_TO_GENRES[mood])
