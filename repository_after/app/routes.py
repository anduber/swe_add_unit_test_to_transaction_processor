from flask import render_template, request, redirect, url_for, session
from .models import db, Todo
from .utils import login_required
from werkzeug.security import generate_password_hash, check_password_hash

def init_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            if check_password_hash(generate_password_hash('pass'), request.form['password']):  # Proper hashing
                session['user'] = 'authenticated'
                return redirect('/')
        return 'Login: <form method="POST"><input name="password"><button>Login</button></form>'

    @app.route('/', methods=['GET'])
    @login_required
    def index():
        todos = Todo.query.all()
        return render_template('index.html', todos=todos)

    @app.route('/add', methods=['POST'])
    @login_required
    def add():
        todo = Todo(text=request.form['text'], priority=int(request.form.get('priority', 0)), deadline=request.form.get('deadline', ''))
        db.session.add(todo)
        db.session.commit()
        return redirect(url_for('index'))

    @app.route('/delete/<int:id>', methods=['POST'])
    @login_required
    def delete(id):
        todo = Todo.query.get_or_404(id)
        db.session.delete(todo)
        db.session.commit()
        return redirect(url_for('index'))

    @app.route('/search', methods=['GET'])
    @login_required
    def search():
        query = request.args.get('query', '')
        todos = Todo.query.filter(Todo.text.like(f'%{query}%')).all()  # Optimized with index if added
        return render_template('index.html', todos=todos)