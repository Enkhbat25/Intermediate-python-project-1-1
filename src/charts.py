"""Charts for the app, each with a one-sentence takeaway.

Every function takes a pandas table and returns (chart, takeaway):
- chart:    an Altair chart (Streamlit shows it with st.altair_chart)
- takeaway: a plain-English sentence computed FROM THE SAME DATA,
            so the sentence changes when the user changes the filters.

We summarise the data with pandas first (counts, averages) and only send
the small summary table to the chart. That keeps charts fast, and the
summary step is easy to test.
"""

import altair as alt
import numpy as np
import pandas as pd

SCATTER_MAX_POINTS = 3000   # more dots than this just makes a grey blob


def rating_vs_votes(matches, picks=None):
    """Scatter: does a popular movie (many votes) also get a high rating?

    Votes are drawn on a log scale because they range from 10 thousand to
    over 3 million. The current suggestions are drawn as big red dots.
    """
    if len(matches) > SCATTER_MAX_POINTS:
        points = matches.sample(SCATTER_MAX_POINTS, random_state=0)
    else:
        points = matches
    points = points[["title", "year", "rating", "votes"]].assign(kind="matching movie")
    if picks is not None and not picks.empty:
        chosen = picks[["title", "year", "rating", "votes"]].assign(kind="suggested")
        points = pd.concat([points, chosen], ignore_index=True)

    chart = alt.Chart(points).mark_circle().encode(
        x=alt.X("votes:Q", scale=alt.Scale(type="log"), title="Number of IMDb votes (log scale)"),
        y=alt.Y("rating:Q", scale=alt.Scale(zero=False), title="IMDb rating"),
        color=alt.Color("kind:N", title="",
                        scale=alt.Scale(domain=["matching movie", "suggested"],
                                        range=["#9aa5b1", "#d62728"])),
        size=alt.condition(alt.datum.kind == "suggested", alt.value(120), alt.value(18)),
        opacity=alt.condition(alt.datum.kind == "suggested", alt.value(1.0), alt.value(0.4)),
        tooltip=["title", "year", "rating", alt.Tooltip("votes:Q", format=",")],
    ).properties(height=380).interactive()   # interactive() = scroll to zoom, drag to pan

    if len(matches) < 3:
        return chart, "Too few movies to see a pattern."
    # Correlation: +1 = more votes always means higher rating, 0 = no link.
    r = np.corrcoef(np.log10(matches["votes"]), matches["rating"])[0, 1]
    if r > 0.3:
        trend = "clearly tend to be rated higher"
    elif r > 0.1:
        trend = "tend to be rated a little higher"
    else:
        trend = "are not rated much differently"
    takeaway = (f"Movies that more people voted on {trend} "
                f"(correlation r = {r:.2f} across {len(matches):,} movies).")
    return chart, takeaway


def decade_counts(matches):
    """Table: how many matching movies came out in each decade."""
    decades = (matches["year"] // 10 * 10).astype(int)
    counts = decades.value_counts().sort_index()
    return pd.DataFrame({"decade": counts.index.astype(str) + "s", "movies": counts.values})


def movies_by_decade(matches):
    """Bar chart: how many matching movies per decade."""
    table = decade_counts(matches)
    chart = alt.Chart(table).mark_bar(color="#1f77b4").encode(
        x=alt.X("decade:N", title="Decade", sort=None),
        y=alt.Y("movies:Q", title="Number of movies"),
        tooltip=["decade", "movies"],
    ).properties(height=300)
    if table.empty:
        return chart, "No movies match these filters."
    top = table.loc[table["movies"].idxmax()]
    share = top["movies"] / table["movies"].sum()
    takeaway = (f"The {top['decade']} have the most matching movies "
                f"({top['movies']:,}, {share:.0%} of them) - partly because IMDb users "
                "vote more on recent films, so more of them pass the 10,000-vote cut.")
    return chart, takeaway


def genre_summary(matches, min_movies=20):
    """Table: one row per genre with its number of movies and average rating.

    A movie with 3 genres counts once in each of them (that's what explode does:
    one row per (movie, genre) pair). Genres with fewer than `min_movies`
    films are dropped, because an average of 3 movies means little.
    """
    pairs = matches[["genre_list", "rating"]].explode("genre_list").dropna()
    table = (pairs.groupby("genre_list")["rating"]
             .agg(movies="count", avg_rating="mean")
             .reset_index()
             .rename(columns={"genre_list": "genre"}))
    table = table[table["movies"] >= min_movies]
    table["avg_rating"] = table["avg_rating"].round(2)
    return table.sort_values("avg_rating", ascending=False).reset_index(drop=True)


def rating_by_genre(matches):
    """Horizontal bars: average rating per genre, best first."""
    table = genre_summary(matches)
    # Dots, not bars: the averages are all between ~6.5 and ~8, and bars must
    # start at 0, which would make every bar look the same length.
    # Bigger dot = more movies in that genre.
    chart = alt.Chart(table).mark_circle(color="#2ca02c", opacity=0.9).encode(
        x=alt.X("avg_rating:Q", title="Average IMDb rating", scale=alt.Scale(zero=False)),
        y=alt.Y("genre:N", sort="-x", title=""),
        size=alt.Size("movies:Q", title="Movies", scale=alt.Scale(range=[40, 500])),
        tooltip=["genre", "movies", "avg_rating"],
    ).properties(height=max(120, 24 * len(table)))
    if table.empty:
        return chart, "Not enough movies per genre to compare (each needs 20+)."
    best, worst = table.iloc[0], table.iloc[-1]
    if len(table) == 1:
        return chart, f"Only {best['genre']} has 20+ matching movies (average {best['avg_rating']})."
    takeaway = (f"{best['genre']} rates highest on average ({best['avg_rating']}), "
                f"{worst['genre']} lowest ({worst['avg_rating']}) - "
                "among genres with at least 20 matching movies.")
    return chart, takeaway


RUNTIME_CAP = 240   # very long films (up to 9+ hours) all go in one "240+" band


def runtime_counts(matches, bin_minutes=10):
    """Table: number of movies in each 10-minute runtime band (90 = 90-99 min)."""
    capped = matches["runtime"].clip(upper=RUNTIME_CAP)
    starts = (capped // bin_minutes * bin_minutes).astype(int)
    counts = starts.value_counts().sort_index()
    table = pd.DataFrame({"minutes": counts.index, "movies": counts.values})
    table["end"] = table["minutes"] + bin_minutes   # right edge of each bar
    return table


def runtime_histogram(matches):
    """Histogram: how long are the matching movies?"""
    table = runtime_counts(matches)
    # Each bar runs from `minutes` to `end` (x to x2), so bars touch like a histogram.
    chart = alt.Chart(table).mark_bar(color="#ff7f0e", stroke="white").encode(
        x=alt.X("minutes:Q", title=f"Runtime in minutes (last bar = {RUNTIME_CAP}+)"),
        x2="end:Q",
        y=alt.Y("movies:Q", title="Number of movies"),
        y2=alt.datum(0),                              # bars grow up from zero
        tooltip=[alt.Tooltip("minutes:Q", title="from minute"), "movies"],
    ).properties(height=300)
    if matches.empty:
        return chart, "No movies match these filters."
    median = int(matches["runtime"].median())
    over_two_hours = (matches["runtime"] > 120).mean()
    takeaway = (f"Half of these movies run {median} minutes or less; "
                f"{over_two_hours:.0%} are longer than 2 hours.")
    return chart, takeaway


def vote_results(tally):
    """Horizontal bars of the room's votes. tally = [(movie_dict, count), ...]"""
    table = pd.DataFrame({
        "movie": [f"{m['title']} ({m['year']})" for m, _ in tally],
        "votes": [count for _, count in tally],
    })
    leader = table["votes"].max()
    table["leading"] = (table["votes"] == leader) & (leader > 0)
    chart = alt.Chart(table).mark_bar().encode(
        x=alt.X("votes:Q", title="Votes", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("movie:N", sort="-x", title="", axis=alt.Axis(labelLimit=220)),
        color=alt.Color("leading:N", legend=None,
                        scale=alt.Scale(domain=[False, True], range=["#9aa5b1", "#d62728"])),
        tooltip=["movie", "votes"],
    ).properties(height=max(120, 32 * len(table)))
    return chart
