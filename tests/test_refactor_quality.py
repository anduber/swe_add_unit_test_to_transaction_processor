import pytest
import timeit
import os

def test_performance():
    # Benchmark query time (simulate 100 todos)
    setup_before = """
from repository_before.app import get_todos
import sqlite3
conn = sqlite3.connect('repository_before/db.sqlite')
for i in range(100):
    conn.execute('INSERT INTO todos (text, priority, deadline) VALUES (?, ?, ?)', (f'Todo {i}', i % 5, '2025-12-31'))
conn.commit()
conn.close()
"""
    time_before = timeit.timeit("get_todos()", setup=setup_before + "def get_todos(): conn = sqlite3.connect('repository_before/db.sqlite'); return conn.execute('SELECT * FROM todos').fetchall()", number=10)

    setup_after = """
from repository_after.app.models import db, Todo
from repository_after.app import create_app
app = create_app()
with app.app_context():
    db.create_all()
    for i in range(100):
        todo = Todo(text=f'Todo {i}', priority=i % 5, deadline='2025-12-31')
        db.session.add(todo)
    db.session.commit()
"""
    time_after = timeit.timeit("Todo.query.all()", setup=setup_after, number=10)

    assert time_after < time_before * 0.8  # After should be faster due to optimization