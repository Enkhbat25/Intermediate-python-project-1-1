"""
prepare_data.py - turn IMDb's huge raw files into one small movies.csv.

Run once (takes about a minute):
    python prepare_data.py
or with custom paths:
    python prepare_data.py --basics path/to/title.basics.tsv.gz \
                           --ratings path/to/title.ratings.tsv.gz \
                           --out data/movies.csv

Why the extra care?
- title.basics.tsv.gz is ~12 million rows. Loading every column at once can
  use several GB of RAM, so we read it in CHUNKS and only the columns we need.
- IMDb writes missing values as the two characters  \\N  -> we tell pandas
  that means "missing" (NaN).
- Some titles contain quote characters ("). By default pandas treats " as a
  special quoting character and silently glues rows together. We switch
  quoting off (csv.QUOTE_NONE) so every line is exactly one row.
"""

import argparse
import csv

import pandas as pd

MIN_VOTES = 10_000          # keep only movies that at least 10k people rated
CHUNK_SIZE = 500_000        # rows of title.basics read at a time
OUTPUT_COLUMNS = ["title", "year", "genres", "rating", "votes", "runtime"]

# Options shared by both read_csv calls (see docstring above for why).
TSV_OPTIONS = {
    "sep": "\t",
    "na_values": "\\N",
    "quoting": csv.QUOTE_NONE,
    "compression": "gzip",
}


def load_popular_ratings(ratings_path, min_votes=MIN_VOTES):
    """Return ratings for titles with at least `min_votes` votes.

    The ratings file is small (~1.5M rows, 3 columns), so we read it whole.
    """
    ratings = pd.read_csv(ratings_path, **TSV_OPTIONS)
    popular = ratings[ratings["numVotes"] >= min_votes]
    return popular


def load_movies_in_chunks(basics_path, wanted_ids, chunk_size=CHUNK_SIZE):
    """Read title.basics piece by piece and keep only wanted movies.

    `wanted_ids` is a set of tconst ids (e.g. "tt0111161") that already
    passed the vote filter, so each chunk shrinks to a handful of rows.
    """
    columns = ["tconst", "titleType", "primaryTitle", "startYear",
               "runtimeMinutes", "genres"]
    kept_pieces = []
    reader = pd.read_csv(basics_path, usecols=columns, dtype=str,
                         chunksize=chunk_size, **TSV_OPTIONS)
    for chunk in reader:
        is_movie = chunk["titleType"] == "movie"
        is_popular = chunk["tconst"].isin(wanted_ids)
        kept_pieces.append(chunk[is_movie & is_popular])
    return pd.concat(kept_pieces, ignore_index=True)


def build_movies_table(basics, ratings):
    """Join basics + ratings and tidy up into the final output columns."""
    merged = basics.merge(ratings, on="tconst", how="inner")
    movies = pd.DataFrame({
        "title": merged["primaryTitle"],
        # Int64 (capital I) is pandas' integer type that allows missing values
        "year": pd.to_numeric(merged["startYear"], errors="coerce").astype("Int64"),
        "genres": merged["genres"].fillna(""),
        "rating": merged["averageRating"],
        "votes": merged["numVotes"].astype(int),
        "runtime": pd.to_numeric(merged["runtimeMinutes"], errors="coerce").astype("Int64"),
    })
    # Most popular first - handy when you eyeball the CSV.
    movies = movies.sort_values("votes", ascending=False).reset_index(drop=True)
    return movies[OUTPUT_COLUMNS]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--basics", default="data/title.basics.tsv.gz")
    parser.add_argument("--ratings", default="data/title.ratings.tsv.gz")
    parser.add_argument("--out", default="data/movies.csv")
    parser.add_argument("--min-votes", type=int, default=MIN_VOTES)
    args = parser.parse_args()

    print(f"Reading ratings from {args.ratings} ...")
    ratings = load_popular_ratings(args.ratings, args.min_votes)
    print(f"  {len(ratings):,} titles have {args.min_votes:,}+ votes")

    print(f"Reading basics from {args.basics} in chunks ...")
    basics = load_movies_in_chunks(args.basics, set(ratings["tconst"]))
    print(f"  {len(basics):,} of them are movies")

    movies = build_movies_table(basics, ratings)
    movies.to_csv(args.out, index=False)
    print(f"Saved {len(movies):,} movies to {args.out}")


if __name__ == "__main__":
    main()
