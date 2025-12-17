from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///repository_after/db.sqlite'
    app.config['SECRET_KEY'] = 'secret'  # For sessions
    db.init_app(app)
    from .routes import init_routes
    init_routes(app)
    return app