from app import db
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    result_file = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)