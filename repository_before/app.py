from flask import Flask, request, render_template_string, redirect
import sqlite3
from werkzeug.security import check_password_hash
from base64 import b64decode
from auth import check_auth  # Duplicated auth import

app = Flask(__name__)
DB = 'repository_before/db.sqlite'

conn = sqlite3.connect(DB, check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY, text TEXT, priority INTEGER, deadline TEXT)')
conn.commit()

HTML = """
<h1>Todo List</h1>
<form method="POST" action="/add">
    <input name="text" placeholder="Todo">
    <input name="priority" type="number" placeholder="Priority">
    <input name="deadline" type="date">
    <button>Add</button>
</form>
<ul>{% for todo in todos %}<li>{{ todo[1] }} (P:{{ todo[2] }}, D:{{ todo[3] }}) <form method="POST" action="/delete/{{ todo[0] }}"><button>Delete</button></form></li>{% endfor %}</ul>
<form method="GET" action="/search"><input name="query" placeholder="Search"><button>Search</button></form>
"""

@app.route('/', methods=['GET'])
def index():
    if not check_auth(request): return 'Unauthorized', 401
    todos = conn.execute('SELECT * FROM todos').fetchall()  # Inefficient full scan
    return render_template_string(HTML, todos=todos)

@app.route('/add', methods=['POST'])
def add():
    if not check_auth(request): return 'Unauthorized', 401
    text = request.form['text']
    priority = request.form.get('priority', 0)
    deadline = request.form.get('deadline', '')
    conn.execute(f"INSERT INTO todos (text, priority, deadline) VALUES ('{text}', {priority}, '{deadline}')")  # SQL injection risk!
    conn.commit()
    return redirect('/')

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete(id):
    if not check_auth(request): return 'Unauthorized', 401
    conn.execute(f'DELETE FROM todos WHERE id = {id}')  # Insecure
    conn.commit()
    return redirect('/')

@app.route('/search', methods=['GET'])
def search():
    if not check_auth(request): return 'Unauthorized', 401
    query = request.args.get('query', '')
    todos = conn.execute(f"SELECT * FROM todos WHERE text LIKE '%{query}%'").fetchall()  # Inefficient, no index
    return render_template_string(HTML, todos=todos)

if __name__ == '__main__':
    app.run(debug=True)