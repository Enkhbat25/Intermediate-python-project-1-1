"""Loading movies.csv, filtering it, and picking suggestions."""

import random

import pandas as pd

from src.moods import genres_for_mood

def load_movies(path):
    """Read movies.csv and add a `genre_list` column (a Python list per row)."""
    movies = pd.read_csv(path)
    movies["genres"] = movies["genres"].fillna("")
    # "Crime,Drama" -> ["Crime", "Drama"]; "" -> []
    movies["genre_list"] = movies["genres"].apply(
        lambda text: [g for g in text.split(",") if g])
    return movies


def all_genres(movies):
    """Sorted list of every genre that appears in the data."""
    found = set()
    for genre_list in movies["genre_list"]:
        found.update(genre_list)
    return sorted(found)


def _has_any(genre_list, wanted):
    """True if the movie has at least one of the wanted genres."""
    return any(g in wanted for g in genre_list)


def filter_movies(movies, genres=None, mood="Any mood", min_rating=0.0,
                  max_runtime=None, year_range=None):
    """Keep only the movies that pass EVERY rule the user set.

    - genres: genres the user ticked. Movie needs at least one of them.
      Empty/None means "any genre".
    - mood: movie needs at least one of the mood's genres.
    - min_rating: IMDb rating must be at least this.
    - max_runtime: length in minutes must be at most this (None = any length).
    - year_range: (first_year, last_year), both included (None = any year).

    All rules must hold together. Picking "Horror" + mood "Feel-good" can
    therefore give zero results - the app shows a message when that happens.
    Each rule is a True/False "mask"; rows where the mask is False are dropped.
    """
    result = movies
    if genres:
        result = result[result["genre_list"].apply(_has_any, wanted=set(genres))]
    mood_genres = genres_for_mood(mood)
    if mood_genres:
        result = result[result["genre_list"].apply(_has_any, wanted=set(mood_genres))]
    result = result[result["rating"] >= min_rating]
    if max_runtime is not None:
        result = result[result["runtime"] <= max_runtime]
    if year_range is not None:
        first_year, last_year = year_range
        # between() includes both ends: 1990-1999 keeps 1990 and 1999.
        result = result[result["year"].between(first_year, last_year)]
    return result


def explain_pick(genre_list, genres=None, mood="Any mood"):
    """Return the genres that made this movie match, e.g. "Crime, Thriller".

    These are the movie's genres that are in the ticked genres or in the
    mood's genres. With no genre/mood chosen, every movie matches, so we
    say so instead of listing genres.
    """
    wanted = set(genres or []) | set(genres_for_mood(mood))
    if not wanted:
        return "any genre"
    matched = [g for g in genre_list if g in wanted]
    return ", ".join(matched)


def add_reasons(picks, genres=None, mood="Any mood"):
    """Add a "matched" column: the genres that made each movie match.

    Returns a new table; the input is not changed.
    """
    picks = picks.copy()
    picks["matched"] = picks["genre_list"].apply(explain_pick, genres=genres, mood=mood)
    return picks


def pick_suggestions(movies, n=5, pool_size=50, seed=None):
    """Pick `n` random movies from the `pool_size` best-rated matches.

    Taking only the very top 5 would show the same films every time;
    sampling from the top 50 keeps quality high but adds variety.
    Pass `seed` to get the same answer every time (used by tests).
    """
    if movies.empty:
        return movies
    # Highest IMDb rating first; when two ratings are equal, more votes first.
    pool = movies.sort_values(["rating", "votes"], ascending=False).head(pool_size)
    rng = random.Random(seed)
    chosen_rows = rng.sample(range(len(pool)), k=min(n, len(pool)))
    picks = pool.iloc[chosen_rows]
    return picks.sort_values("rating", ascending=False).reset_index(drop=True)
