from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Snapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(80), nullable=False)
    metric = db.Column(db.String(200), nullable=False)
    timestamp_capture = db.Column(db.DateTime, nullable=False, default=datetime.now())

    def __repr__(self):
        return f'<Snapshot {self.device_id}>'