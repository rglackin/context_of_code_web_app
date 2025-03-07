from flask import Blueprint, jsonify, request
from models import db, Snapshot
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return jsonify({"message": "Hello World"})

@bp.route('/api/data', methods=['GET'])
def get_data():
    snapshots = Snapshot.query.all()
    return jsonify([{
        'device_id': snapshot.device_id,
        'metric': snapshot.metric,
        'timestamp_capture': snapshot.timestamp_capture
    } for snapshot in snapshots])

@bp.route('/api/data', methods=['POST'])
def add_data():
    data = request.get_json()
    device_id = data.get('device_id')
    metric = data.get('metric')
    timestamp_capture = data.get('timestamp_capture')

    if not device_id or not metric or not timestamp_capture:
        return jsonify({"error": "Invalid data"}), 400

    new_snapshot = Snapshot(
        device_id=device_id,
        metric=metric,
        timestamp_capture=datetime.fromisoformat(timestamp_capture)
    )
    db.session.add(new_snapshot)
    db.session.commit()

    return jsonify({"message": "Data snapshot added successfully"}), 201