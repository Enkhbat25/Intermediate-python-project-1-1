"""Shared test data: a tiny fake movies table so tests run instantly."""

import pandas as pd
import pytest

# (pytest.ini adds the project folder to the import path, so `import src` works.)


@pytest.fixture
def movies(tmp_path):
    from src.recommender import load_movies

    csv_path = tmp_path / "movies.csv"
    pd.DataFrame([
        {"title": "Funny Dog", "year": 2001, "genres": "Comedy,Family", "rating": 7.0, "votes": 20000, "runtime": 90},
        {"title": "Dark Night", "year": 2008, "genres": "Crime,Thriller", "rating": 9.0, "votes": 90000, "runtime": 150},
        {"title": "Scary House", "year": 2015, "genres": "Horror", "rating": 5.5, "votes": 15000, "runtime": 95},
        {"title": "Love Story", "year": 1999, "genres": "Romance,Drama", "rating": 8.0, "votes": 30000, "runtime": 120},
        {"title": "Space Trip", "year": 2020, "genres": "Sci-Fi,Adventure", "rating": 7.5, "votes": 50000, "runtime": 140},
        {"title": "Dune", "year": 1984, "genres": "Sci-Fi", "rating": 6.3, "votes": 40000, "runtime": 137},
        {"title": "Dune", "year": 2021, "genres": "Sci-Fi", "rating": 8.0, "votes": 90000, "runtime": 155},
        {"title": "No Genre", "year": 2010, "genres": None, "rating": 6.0, "votes": 11000, "runtime": 100},
    ]).to_csv(csv_path, index=False)
    return load_movies(csv_path)
