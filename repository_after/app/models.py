from . import db

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200))
    priority = db.Column(db.Integer)
    deadline = db.Column(db.String(10))

    def __init__(self, text, priority, deadline):
        self.text = text
        self.priority = priority
        self.deadline = deadline