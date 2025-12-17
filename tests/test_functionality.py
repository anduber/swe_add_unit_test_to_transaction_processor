import pytest
from flask.testing import FlaskClient
import sqlite3
import os

@pytest.fixture
def before_client():
    from repository_before.app import app
    # Init DB if needed
    if not os.path.exists('repository_before/db.sqlite'):
        conn = sqlite3.connect('repository_before/db.sqlite')
        conn.execute('CREATE TABLE todos (id INTEGER PRIMARY KEY, text TEXT, priority INTEGER, deadline TEXT)')
        conn.close()
    return app.test_client()

@pytest.fixture
def after_client():
    from repository_after.app.main import app
    # Init DB if needed (models.py handles it)
    from repository_after.app.models import db, Todo
    db.create_all()
    return app.test_client()

@pytest.mark.parametrize("client_func", ["before_client", "after_client"])
def test_add_view_delete_search(client_func, request):
    client: FlaskClient = request.getfixturevalue(client_func)
    # Mock auth (assume user:pass for before, session for after)
    if "before" in client_func:
        client.environ_base['HTTP_AUTHORIZATION'] = 'Basic dXNlcjpwYXNz'  # user:pass
    else:
        with client:
            client.get('/')  # Simulate session start

    # Add todo
    client.post('/add', data={'text': 'Test Todo', 'priority': 1, 'deadline': '2025-12-31'})
    # View
    response = client.get('/')
    assert b'Test Todo' in response.data
    # Search
    response = client.get('/search?query=Test')
    assert b'Test Todo' in response.data
    # Delete
    client.post('/delete/1')  # Assume ID 1
    response = client.get('/')
    assert b'Test Todo' not in response.data