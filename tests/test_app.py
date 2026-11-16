"""Smoke test: run the real app headlessly with Streamlit's AppTest."""

from streamlit.testing.v1 import AppTest


def test_app_suggest_create_room_and_vote():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert not at.exception

    at.button(key="suggest").click().run()
    assert len(at.dataframe) == 1
    assert len(at.dataframe[0].value) == 5

    at.text_input(key="host_name").input("Bat").run()
    at.button(key="create").click().run()
    assert not at.exception
    code = at.session_state.code_box
    assert len(code) == 4

    at.radio(key="vote_choice").set_value(2).run()
    at.button(key="vote").click().run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert any("Winner so far" in s.value for s in at.subheader)


def test_friend_joins_with_code_and_votes():
    """A second phone = a second AppTest. They share the same RoomStore,
    because st.cache_resource is shared across sessions in one process."""
    host = AppTest.from_file("../app.py", default_timeout=30).run()
    host.button(key="suggest").click().run()
    host.text_input(key="host_name").input("Host").run()
    host.button(key="create").click().run()
    code = host.session_state.code_box

    friend = AppTest.from_file("../app.py", default_timeout=30).run()
    friend.text_input(key="code_box").input(code.lower()).run()
    friend.text_input(key="name_box").input("Friend").run()
    friend.button(key="vote").click().run()
    assert not friend.error, [e.value for e in friend.error]
    assert "1 people voted" in friend.caption[0].value


def test_wrong_code_shows_error():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    at.text_input(key="code_box").input("ZZZZ").run()
    assert "No room called ZZZZ" in at.error[0].value


def test_filters_and_reasons_show_in_table():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    at.selectbox[0].set_value("Scare me").run()
    at.slider[1].set_value((1990, 1999)).run()          # release years
    at.radio[0].set_value("Up to 2 hours").run()       # runtime choice
    at.button(key="suggest").click().run()
    assert not at.exception
    table = at.dataframe[0].value
    assert len(table) == 5
    assert table["year"].between(1990, 1999).all()
    assert (table["runtime"] <= 120).all()
    assert table["matched"].str.contains("Horror").all()
    assert "score" not in table.columns


def test_how_many_slider_changes_number_of_suggestions():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    at.slider[2].set_value(10).run()                    # "How many suggestions?"
    assert at.button(key="suggest").label == "🎲 Suggest 10 movies"
    at.button(key="suggest").click().run()
    assert len(at.dataframe[0].value) == 10


def test_room_with_ten_movies_accepts_vote_for_last_one():
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    at.slider[2].set_value(10).run()
    at.button(key="suggest").click().run()
    at.text_input(key="host_name").input("Bat").run()
    at.button(key="create").click().run()
    assert len(at.radio(key="vote_choice").options) == 10
    at.radio(key="vote_choice").set_value(9).run()      # the 10th movie
    at.button(key="vote").click().run()
    assert not at.error, [e.value for e in at.error]
    assert "1 people voted" in at.caption[-1].value
