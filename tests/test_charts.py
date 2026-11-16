"""Chart helpers: check the summary tables and that takeaways follow the data."""

from src import charts


def test_decade_counts(movies):
    table = charts.decade_counts(movies)
    assert table["movies"].sum() == len(movies)
    assert "2000s" in set(table["decade"])


def test_genre_summary_counts_each_genre_of_a_movie(movies):
    table = charts.genre_summary(movies, min_movies=1)
    sci_fi = table[table["genre"] == "Sci-Fi"].iloc[0]
    assert sci_fi["movies"] == 3          # Space Trip + two Dunes


def test_genre_summary_drops_small_genres(movies):
    assert charts.genre_summary(movies, min_movies=20).empty


def test_runtime_counts_use_ten_minute_bands(movies):
    table = charts.runtime_counts(movies)
    assert set(table["minutes"]) <= set(range(0, 300, 10))
    assert table["movies"].sum() == len(movies)


def test_every_chart_builds_with_a_takeaway(movies):
    for make in (charts.rating_vs_votes, charts.movies_by_decade,
                 charts.rating_by_genre, charts.runtime_histogram):
        chart, takeaway = make(movies)
        chart.to_dict()                    # raises if the chart spec is invalid
        assert isinstance(takeaway, str) and takeaway


def test_runtime_takeaway_uses_median(movies):
    _, takeaway = charts.runtime_histogram(movies)
    assert str(int(movies["runtime"].median())) in takeaway



def test_vote_chart_highlights_leader():
    tally = [({"title": "A", "year": 2000}, 1), ({"title": "B", "year": 2001}, 3)]
    spec = charts.vote_results(tally).to_dict()
    rows = list(spec["datasets"].values())[0]
    assert [r["leading"] for r in rows] == [False, True]
