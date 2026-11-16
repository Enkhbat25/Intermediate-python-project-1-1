"""Run prepare_data on tiny fake IMDb files (same format as the real ones)."""

import gzip
from pathlib import Path

import pandas as pd

import prepare_data

BASICS = (
    "tconst\ttitleType\tprimaryTitle\toriginalTitle\tisAdult\tstartYear\tendYear\truntimeMinutes\tgenres\n"
    "tt1\tmovie\tBig Hit\tBig Hit\t0\t2000\t\\N\t120\tAction,Drama\n"
    "tt2\tmovie\tSmall Film\tSmall Film\t0\t2001\t\\N\t90\tDrama\n"
    "tt3\ttvSeries\tPopular Show\tPopular Show\t0\t2005\t2010\t45\tComedy\n"
    'tt4\tmovie\t"Quoted" Title\t"Quoted" Title\t0\t\\N\t\\N\t\\N\t\\N\n'
)
RATINGS = (
    "tconst\taverageRating\tnumVotes\n"
    "tt1\t8.1\t50000\n"
    "tt2\t7.0\t500\n"
    "tt3\t9.0\t99999\n"
    "tt4\t6.5\t10000\n"
)


def write_gz(path, text):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def test_full_pipeline(tmp_path):
    basics_path = tmp_path / "basics.tsv.gz"
    ratings_path = tmp_path / "ratings.tsv.gz"
    write_gz(basics_path, BASICS)
    write_gz(ratings_path, RATINGS)

    ratings = prepare_data.load_popular_ratings(ratings_path)
    basics = prepare_data.load_movies_in_chunks(basics_path, set(ratings["tconst"]),
                                                chunk_size=2)  # force several chunks
    movies = prepare_data.build_movies_table(basics, ratings)

    assert list(movies.columns) == prepare_data.OUTPUT_COLUMNS
    # tt2 has too few votes, tt3 is a TV series -> both dropped.
    # tt4 has exactly 10,000 votes -> kept (the rule is "10,000 or more").
    assert set(movies["title"]) == {"Big Hit", '"Quoted" Title'}
    quoted = movies[movies["title"] == '"Quoted" Title'].iloc[0]
    assert pd.isna(quoted["year"]) and pd.isna(quoted["runtime"])
    assert movies.iloc[0]["title"] == "Big Hit"   # sorted by votes


def test_shipped_csv_looks_right():
    movies = pd.read_csv(Path(__file__).parent.parent / "data" / "movies.csv")
    assert list(movies.columns) == prepare_data.OUTPUT_COLUMNS
    assert (movies["votes"] >= 10_000).all()
    assert len(movies) > 1000
