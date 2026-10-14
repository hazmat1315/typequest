"""Shared test setup.  Owner: George (lead tester).

Every test gets its own empty temporary database, so tests never touch the
real typequest.db and cannot affect each other.
"""

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret")  # must be set before app is imported

from app import app  # noqa: E402
from models.database import Database  # noqa: E402


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    database.create_tables()
    app.config["DATABASE"] = database.db_path
    return database


@pytest.fixture
def client(db):
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def register(client, username="typer01", password="secret12"):
    return client.post("/register", data={"username": username, "password": password})


def login(client, username="typer01", password="secret12"):
    return client.post("/login", data={"username": username, "password": password})


def page_text(response):
    return response.get_data(as_text=True)
