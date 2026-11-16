# 🍿 Movie Night Picker

A Streamlit app that suggests 5 movies (or up to 10) for your mood, then lets your friends
vote on them from their own phones using a 4-character room code.

**Data: IMDb Non-Commercial Datasets** (https://developer.imdb.com/non-commercial-datasets/).
Used for personal, non-commercial purposes only.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

`data/movies.csv` (12,700 movies, ~700 KB) is already included, so you don't
need the big IMDb files to run the app.

### Letting friends join from their phones

The phones must be able to reach the computer running the app:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Then everyone on the **same Wi-Fi** opens `http://<your-laptop-ip>:8501`.
After you create a room, the URL becomes `...:8501/?room=AB3K`; sending that
link fills in the code automatically.

## Rebuilding movies.csv

1. Download `title.basics.tsv.gz` and `title.ratings.tsv.gz` from IMDb into `data/`.
2. Run `python prepare_data.py` (about 30 seconds).

It keeps rows where `titleType == "movie"` and `numVotes >= 10,000`, and writes
`title, year, genres, rating, votes, runtime`.

## How it works

```
prepare_data.py      raw IMDb TSVs  ->  data/movies.csv  (run once)
app.py               the Streamlit page (UI only, no real logic)
src/moods.py         mood name -> list of genres
src/recommender.py   load CSV, filter by genre/mood/rating, pick 5
src/rooms.py         RoomStore: create rooms, vote, count, find winner
src/charts.py        Altair charts + takeaway sentences
tests/               pytest tests for every module + the app itself
```

- **Filtering:** a movie must have at least one ticked genre **and** at least
  one genre of the chosen mood. Horror + "Feel-good" can therefore return
  nothing; the app says so.
- **Other filters:** minimum rating, a release-year range slider and a
  runtime choice ("Up to 2 hours" keeps films of 120 minutes or less). Each
  rule in `filter_movies` is a True/False mask on the table; a movie must pass
  all of them.
- **Why was it picked?** The table shows a "matched genres" column: the
  movie's genres that are in your ticked genres or your mood (`explain_pick`).
- **Suggestions:** the 50 highest-*rated* matches (ties: more votes first) are taken and 5 (or however many the
  "How many suggestions?" slider says, 3-10) are chosen at random,
  so pressing the button again gives new ideas.
- **Ranking by raw IMDb rating:** simple and easy to check, but a film rated
  9.1 by 18 thousand fans ranks above one rated 9.0 by 2 million people. The
  10,000-vote minimum limits this, but doesn't remove it.
- **Rooms:** `st.cache_resource` returns the *same* `RoomStore` object to every
  browser session, so all phones see the same rooms. (`st.cache_data` would
  hand each session its own copy, and votes would never meet.)
- **Live results:** the results section is an `st.fragment(run_every="3s")`,
  so it re-runs by itself every 3 seconds and new votes show up without anyone
  pressing anything.
- **One vote per person:** votes are stored in a dict keyed by the voter's name
  (trimmed, lower-case). Voting again replaces your old vote.
- **Same-title movies:** votes store the movie's *position* in the room, not its
  title, because titles repeat (542 titles in movies.csv appear more than once,
  e.g. "Dune" 1984 and 2021).
- **Winner:** most votes; ties go to the higher IMDb rating, then title A-Z.

## Charts (📊 Explore the data tab + the other tabs)

Every chart uses only the movies that match the sidebar filters, has hover
tooltips, and has a **Takeaway** sentence under it. The sentence is computed
from the same data (`src/charts.py`), so it changes when the filters change.

| Chart | Type | What it answers |
|---|---|---|
| Are popular movies also better rated? | scatter, log scale, zoom/pan | Do more votes mean a higher rating? Takeaway gives the correlation r. Current suggestions are red. |
| Which genres rate best? | dot plot (dot size = number of movies) | Average rating per genre (genres with 20+ movies). |
| When were they made? | bar chart | Movies per decade, and why recent decades dominate. |
| How long are they? | histogram, 10-minute bands | Median runtime and share over 2 hours. |
| Live results (Vote tab) | bar chart, leader in red | Votes per movie, refreshes every 3 seconds. |

## Running the tests

```bash
pytest
```

57 tests: moods, filtering, scoring, chart summaries, the data pipeline (on tiny fake IMDb
files, including a title with quote marks), the room store (including 100
threads voting at the same moment), and the real app driven by Streamlit's
`AppTest` (host creates a room, a second session joins with the code and votes).

## Known limits (be ready to defend these)

These are deliberate simplifications for a course project. Know them before
someone asks.

1. **Rooms live in RAM of one server process.** Restart the server (or let
   Streamlit Community Cloud put the app to sleep) and every room is gone. If
   the app ran on several servers/processes behind a load balancer, each would
   have its own rooms and friends could "lose" the room. A real app would use
   a database or Redis.
2. **Thread safety is handled by a lock, not by Streamlit.** Streamlit runs
   each browser session in its own thread, and `cache_resource` does *not*
   make the shared object safe. `RoomStore` wraps every read and write in a
   `threading.Lock`; remove it and simultaneous votes can be lost or a
   `dict changed size during iteration` error can appear.
3. **"Live" means polling every 3 seconds.** Each open phone re-runs the
   results fragment every 3 s whether anything changed or not. Fine for a
   few friends; wasteful for hundreds of users.
4. **One-vote-per-person is honour-based.** Anyone can type a friend's name and
   overwrite their vote, or type a new name to vote twice. Fixing that needs
   real identity (login) or at least a per-device token.
5. **Room codes are guessable.** 4 characters from 32 symbols = ~1 million
   codes. Fine among friends; not a security feature.
6. **Old rooms expire after 6 hours**, but only when someone creates a new
   room (that's when cleanup runs).
7. **Data is a snapshot.** Ratings/votes are frozen at the moment you ran
   `prepare_data.py`; the 10,000-vote cut-off also hides newer and niche films.
8. **IMDb genres are coarse.** Max 3 genres per film, and the mood -> genre
   mapping in `src/moods.py` is a personal judgement call.
