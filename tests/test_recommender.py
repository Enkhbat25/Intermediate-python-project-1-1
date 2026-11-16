from src.recommender import (add_reasons, all_genres, explain_pick, filter_movies,
                             pick_suggestions)


def test_missing_genres_become_empty_list(movies):
    row = movies[movies["title"] == "No Genre"].iloc[0]
    assert row["genre_list"] == []


def test_all_genres_sorted_and_unique(movies):
    genres = all_genres(movies)
    assert genres == sorted(set(genres))
    assert "Horror" in genres


def test_no_filters_keeps_everything(movies):
    assert len(filter_movies(movies)) == len(movies)


def test_genre_filter_matches_any_selected_genre(movies):
    titles = set(filter_movies(movies, genres=["Horror", "Romance"])["title"])
    assert titles == {"Scary House", "Love Story"}


def test_mood_filter(movies):
    titles = set(filter_movies(movies, mood="Edge of my seat")["title"])
    assert titles == {"Dark Night"}


def test_genre_and_mood_must_both_match(movies):
    # Horror movies that are also feel-good: none.
    assert filter_movies(movies, genres=["Horror"], mood="Feel-good").empty


def test_min_rating(movies):
    assert (filter_movies(movies, min_rating=8.0)["rating"] >= 8.0).all()


def test_max_runtime(movies):
    assert (filter_movies(movies, max_runtime=100)["runtime"] <= 100).all()


def test_pick_returns_five_unique_movies(movies):
    picks = pick_suggestions(movies, n=5, seed=1)
    assert len(picks) == 5
    assert not picks.duplicated(["title", "year"]).any()


def test_pick_is_repeatable_with_seed(movies):
    a = pick_suggestions(movies, seed=42)
    b = pick_suggestions(movies, seed=42)
    assert a.equals(b)


def test_pick_only_from_top_pool(movies):
    # Best ratings: Dark Night 9.0, then Dune 2021 and Love Story both 8.0.
    # Tie -> more votes first, so Dune 2021 (90k) beats Love Story (30k).
    picks = pick_suggestions(movies, n=2, pool_size=2, seed=0)
    assert set(zip(picks["title"], picks["year"])) == {("Dark Night", 2008), ("Dune", 2021)}


def test_pick_with_fewer_movies_than_n(movies):
    assert len(pick_suggestions(movies.head(3), n=5)) == 3


def test_pick_from_empty(movies):
    assert pick_suggestions(movies.iloc[0:0]).empty


def test_year_range_includes_both_ends(movies):
    years = filter_movies(movies, year_range=(1999, 2008))["year"]
    assert set(years) == {1999, 2001, 2008}


def test_runtime_under_two_hours(movies):
    result = filter_movies(movies, max_runtime=120)
    assert "Love Story" in set(result["title"])     # exactly 120 min is kept
    assert (result["runtime"] <= 120).all()


def test_all_filters_together(movies):
    result = filter_movies(movies, mood="Mind-bending", min_rating=7.0,
                           max_runtime=150, year_range=(2000, 2025))
    assert list(result["title"]) == ["Space Trip"]


def test_explain_pick_lists_matching_genres():
    assert explain_pick(["Crime", "Drama", "Thriller"], mood="Edge of my seat") == "Crime, Thriller"


def test_explain_pick_combines_ticked_genres_and_mood():
    assert explain_pick(["Comedy", "Romance"], genres=["Romance"], mood="Feel-good") == "Comedy, Romance"


def test_explain_pick_with_no_choices():
    assert explain_pick(["Drama"]) == "any genre"


def test_add_reasons_adds_columns_without_changing_input(movies):
    picks = pick_suggestions(movies, seed=1)
    explained = add_reasons(picks, mood="Mind-bending")
    assert "matched" in explained.columns
    assert "matched" not in picks.columns


def test_pick_asked_number(movies):
    assert len(pick_suggestions(movies, n=7, seed=3)) == 7
