"""
Movie Night Picker - Streamlit app.

Goal: help a group of friends agree on a good movie quickly.
1) Filter ~12,700 well-known IMDb movies by mood, genre, rating, year, length.
2) Get a few suggestions picked from the highest-rated matches.
3) Vote on them together, each on their own phone, with a room code.

Run locally:   streamlit run app.py
Phones on the same Wi-Fi:  streamlit run app.py --server.address 0.0.0.0
Online: deploy on Streamlit Community Cloud (see README).
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from src import charts
from src.moods import MOOD_TO_GENRES
from src.recommender import (add_reasons, all_genres, filter_movies, load_movies,
                             pick_suggestions)
from src.rooms import RoomStore

DATA_PATH = Path(__file__).parent / "data" / "movies.csv"

# Label shown in the app -> longest runtime allowed, in minutes (None = no limit).
RUNTIME_CHOICES = {
    "Any length": None,
    "Up to 1.5 hours": 90,
    "Up to 2 hours": 120,
    "Up to 2.5 hours": 150,
}

st.set_page_config(page_title="Movie Night Picker", page_icon="🍿", layout="wide")


# ---------- shared resources ----------

@st.cache_data
def get_movies():
    """Read the CSV once; every rerun reuses the result."""
    return load_movies(DATA_PATH)


@st.cache_resource
def get_room_store():
    """ONE RoomStore object shared by every user of this server process.

    cache_resource hands everybody the *same* object (not a copy), which is
    exactly what we need for shared rooms. cache_data would give each user
    their own copy, and votes would never meet.
    """
    return RoomStore()


movies = get_movies()
store = get_room_store()

# Remember things between reruns for THIS browser tab only.
# "code_box" and "name_box" are the keys of the two text boxes in the Vote tab,
# so setting them here (or below) fills those boxes in for the user.
st.session_state.setdefault("suggestions", None)
st.session_state.setdefault("code_box", st.query_params.get("room", ""))
st.session_state.setdefault("name_box", "")


def movie_label(movie):
    """'Inception (2010) - 8.8 *' style label for lists and radio buttons."""
    return f"{movie['title']} ({movie['year']}) - ⭐ {movie['rating']}"


def show_chart(chart_and_takeaway):
    """Draw a chart and its one-line takeaway under it."""
    chart, takeaway = chart_and_takeaway
    st.altair_chart(chart, width="stretch")
    st.markdown(f"**Takeaway:** {takeaway}")


# ---------- sidebar: the filters (used by every tab) ----------

with st.sidebar:
    st.header("🎛️ Your filters")
    mood = st.selectbox("What's the mood?", list(MOOD_TO_GENRES))
    genres = st.multiselect("Genres (optional)", all_genres(movies))
    min_rating = st.slider("Minimum IMDb rating", 0.0, 10.0, 6.5, 0.1)
    # Giving a slider a (low, high) pair as its value turns it into a range slider.
    first_year, last_year = int(movies["year"].min()), int(movies["year"].max())
    year_range = st.slider("Release years", first_year, last_year, (first_year, last_year))
    runtime_label = st.radio("How long?", list(RUNTIME_CHOICES))
    max_runtime = RUNTIME_CHOICES[runtime_label]
    # How many movies to suggest: 5 by default, up to 10.
    how_many = st.slider("How many suggestions?", 3, 10, 5)

# Filtering runs on every rerun, so the charts follow the sidebar instantly.
matches = filter_movies(movies, genres=genres, mood=mood, min_rating=min_rating,
                        max_runtime=max_runtime, year_range=year_range)


# ---------- header ----------

st.title("🍿 Movie Night Picker")
st.markdown(
    "**Goal:** stop the 30-minute *\"what should we watch?\"* argument. "
    "Filter 12,700 well-known movies, get a short list of top-rated picks, "
    "then let everyone vote from their own phone.")

col1, col2, col3 = st.columns(3)
col1.metric("Movies matching your filters", f"{len(matches):,}")
col2.metric("Average rating", f"{matches['rating'].mean():.1f}" if len(matches) else "-")
col3.metric("Median length", f"{int(matches['runtime'].median())} min" if len(matches) else "-")

# A key keeps the open tab when the page reruns. Friends who arrive with an
# invite link (?room=CODE) start on the Vote tab.
TAB_NAMES = ["🎬 Pick movies", "📊 Explore the data", "🗳️ Vote", "📖 About the data"]
start_tab = TAB_NAMES[2] if st.query_params.get("room") else TAB_NAMES[0]
tab_pick, tab_explore, tab_vote, tab_about = st.tabs(TAB_NAMES, default=start_tab,
                                                     key="active_tab")


# ---------- tab 1: suggestions ----------

with tab_pick:
    if st.button(f"🎲 Suggest {how_many} movies", type="primary", key="suggest"):
        picks = pick_suggestions(matches, n=how_many)
        # Work out the "why" columns now, using the same choices as the filter.
        st.session_state.suggestions = add_reasons(picks, genres=genres, mood=mood)
        st.session_state.match_count = len(matches)

    suggestions = st.session_state.suggestions
    if suggestions is None:
        st.info("Set your filters in the sidebar, then press the button.")
    elif suggestions.empty:
        st.warning("No movies match. Try fewer genres, another mood, or a lower rating.")
    else:
        st.dataframe(
            suggestions[["title", "year", "runtime", "matched", "rating", "votes"]],
            hide_index=True,
            width="stretch",
            column_config={
                "runtime": st.column_config.NumberColumn("minutes"),
                "matched": st.column_config.TextColumn("why: matched genres"),
                "rating": st.column_config.ProgressColumn(
                    "IMDb rating", min_value=0, max_value=10, format="%.1f"),
                "votes": st.column_config.NumberColumn("votes", format="%d"),
            },
        )
        st.caption(f"Picked at random from the 50 highest-rated of "
                   f"{st.session_state.match_count:,} matching movies. "
                   "Press the button again for different picks.")

        st.subheader("Start a vote with these movies")
        host_name = st.text_input("Your name (host)", key="host_name")
        if st.button("Create a voting room with these movies", key="create"):
            if not host_name.strip():
                st.error("Enter your name first.")
            else:
                candidates = suggestions[["title", "year", "rating"]].to_dict("records")
                code = store.create_room(host_name, candidates)
                # Pre-fill the Vote tab's boxes, so the host can vote at once.
                st.session_state.code_box = code
                st.session_state.name_box = host_name
                # Put the code in the URL too: https://...app/?room=AB3K
                st.query_params["room"] = code
                st.success(f"Room **{code}** created - open the 🗳️ Vote tab and "
                           "share the code (or this page's link) with friends.")


# ---------- tab 2: charts that follow the filters ----------

with tab_explore:
    st.markdown("Every chart below uses **only the movies matching your sidebar "
                "filters**, so change a filter and watch them update. Hover for "
                "details; on the scatter, scroll to zoom and drag to pan.")
    if matches.empty:
        st.warning("No movies match your filters, so there is nothing to chart.")
    else:
        st.subheader("Are popular movies also better rated?")
        show_chart(charts.rating_vs_votes(matches, st.session_state.suggestions))

        left, right = st.columns(2)
        with left:
            st.subheader("Which genres rate best?")
            show_chart(charts.rating_by_genre(matches))
        with right:
            st.subheader("When were they made?")
            show_chart(charts.movies_by_decade(matches))
            st.subheader("How long are they?")
            show_chart(charts.runtime_histogram(matches))


# ---------- tab 3: voting room ----------

@st.fragment(run_every="3s")
def live_results(code):
    """Re-runs by itself every 3 seconds, so other people's votes appear
    without anyone pressing a button (only this part of the page reloads)."""
    st.subheader("Live results")
    tally = store.results(code)
    st.altair_chart(charts.vote_results(tally), width="stretch")
    st.caption(f"{store.voter_count(code)} people voted. Updates every 3 seconds.")

    winner = store.winner(code)
    if winner:
        st.subheader(f"🏆 Winner so far: {winner['title']} ({winner['year']})")


def vote_tab():
    """Join a room, vote, and watch results. Uses `return` (not st.stop) so
    the tabs after this one still get drawn."""
    st.markdown("Create a room in **🎬 Pick movies**, or type the code a friend gave you.")
    col_code, col_name = st.columns(2)
    typed_code = col_code.text_input("Room code", key="code_box").strip().upper()
    typed_name = col_name.text_input("Your name", key="name_box")

    if not typed_code:
        st.info("No room yet.")
        return
    if not store.room_exists(typed_code):
        st.error(f"No room called {typed_code}. Check the code "
                 "(rooms vanish if the server restarts).")
        return

    st.success(f"Room **{typed_code}** - tell friends to open this app and enter that code.")
    candidates = store.get_candidates(typed_code)
    choice = st.radio("Your vote", range(len(candidates)), key="vote_choice",
                      format_func=lambda i: movie_label(candidates[i]))
    if st.button("✅ Vote", key="vote"):
        try:
            store.vote(typed_code, typed_name, choice)
            st.toast(f"Vote saved for {candidates[choice]['title']}")
        except ValueError as err:
            st.error(str(err))
    live_results(typed_code)


with tab_vote:
    vote_tab()


# ---------- tab 4: dataset documentation ----------

with tab_about:
    st.subheader("Source")
    st.markdown(
        "**Data: IMDb Non-Commercial Datasets** "
        "([developer.imdb.com/non-commercial-datasets](https://developer.imdb.com/non-commercial-datasets/)), "
        "files `title.basics.tsv.gz` and `title.ratings.tsv.gz`, downloaded **November 2026**. "
        "Used for personal, non-commercial (course) purposes.")

    st.subheader("How the raw data was cleaned (`prepare_data.py`)")
    st.markdown("""
1. **Read safely.** `title.basics` has ~12 million rows, so it is read in chunks of
   500,000 and only 6 of its 9 columns. IMDb writes missing values as `\\N`, which is
   turned into a real "missing" value. Quote marks inside titles would make pandas
   glue rows together, so quoting is switched off (`csv.QUOTE_NONE`).
2. **Filter.** Keep titles with **10,000+ votes** (18,448 titles), then keep only
   `titleType == "movie"` (TV series, episodes and shorts dropped): **12,700 movies**.
3. **Join and tidy.** Join the two files on the IMDb id, convert year and runtime to
   numbers, keep 6 columns, sort by votes.
4. **In the app.** Split the genre text into a list, filter by the sidebar choices,
   and rank by **IMDb rating** (ties: more votes first).
""")

    st.subheader("Columns in `movies.csv`")
    st.table(pd.DataFrame({
        "column": ["title", "year", "genres", "rating", "votes", "runtime"],
        "meaning": ["Main title (IMDb primaryTitle)", "Release year",
                    "Up to 3 IMDb genres, comma separated",
                    "Average IMDb user rating, 1-10", "Number of IMDb user ratings",
                    "Length in minutes"],
    }))

    st.subheader("Quality checks (computed live from the file)")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Movies", f"{len(movies):,}")
    q2.metric("Years covered", f"{first_year}-{last_year}")
    q3.metric("Fewest votes", f"{movies['votes'].min():,}")
    q4.metric("Movies with no genre", int((movies["genres"] == "").sum()))
    st.markdown(
        f"Missing values: **{int(movies[['title', 'year', 'rating', 'votes', 'runtime']].isna().sum().sum())}** "
        f"in title/year/rating/votes/runtime. "
        f"**{int(movies.duplicated('title', keep=False).sum()):,}** rows share a title with "
        "another movie (remakes like *Dune* 1984 and 2021), so the app never uses the "
        "title alone to identify a movie.")
    st.markdown("**Limits:** ratings are a snapshot from the download date; the 10,000-vote "
                "cut hides very new and niche films; IMDb voters are not a random sample "
                "of all viewers.")
