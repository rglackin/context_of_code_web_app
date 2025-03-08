from flask import Blueprint, jsonify, request
from models import *
from datetime import datetime
from dto_datamodel import DTO_Aggregator
from aggregator_mapping import map_dto_to_model
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dto_datamodel import *

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
@bp.route('/')
def home():
    return jsonify({"message": "Hello World"})

def add_aggregator():
    try:
        session = db.session
        data = request.get_json()
        logger.info("Received data")
        if not data:
            return jsonify({"error": "Invalid data"}), 400
        
        # Deserialize JSON to DTO
        logger.info("Deserializing JSON to DTO")
        logger.debug(f"Data: {data}")
        aggregator_dto = DTO_Aggregator.from_dict(data)
        logger.info("Deserialization complete")
        
        # Map DTO to models and save to the database
        logger.info("Mapping DTO to Model")
        map_dto_to_model(aggregator_dto, session)
        logger.info("Mapping complete")
        
        return jsonify({"message": "Aggregator added successfully"}), 201
    except Exception as e:
        logger.error(f"Error in add aggregator route: {e}")
        if session is not None:
            logger.error("Rolling back session")
            try:
                session.rollback()
                session.close()
            except Exception as e:
                logger.error(f"Error rolling back session: {e}")
            
        return jsonify({
                        "status": "error",
                        "message": str(e)
                        }), 500

def get_aggregator():
    try:
        session = db.session
        uuid = request.args.get('uuid')
        
        if uuid:
            logger.info(f"Fetching aggregator with UUID: {uuid}")
            # Fetch a single aggregator by UUID
            aggregator = session.query(Snapshot).filter_by(guid=uuid).first()
            if not aggregator:
                return jsonify({"error": "Aggregator not found"}), 404
            aggregator_dto = DTO_Aggregator(
                guid=aggregator.guid,
                name=aggregator.name,
                devices=[
                    DTO_Device(
                        name=device.name,
                        snapshots=[
                            DTO_Snapshot(
                                timestamp_capture=datetime.fromtimestamp(snapshot.client_timestamp_epoch),
                                timezone_mins=snapshot.client_timezon_mins,
                                metrics=[
                                    DTO_Metric(
                                        name=metric.device_metric_type.name,
                                        value=metric.value
                                    ) for metric in snapshot.metrics
                                ]
                            ) for snapshot in device.snapshots
                        ]
                    ) for device in aggregator.devices
                ]
            )
            return jsonify(aggregator_dto.to_dict()), 200
        else:
            # Fetch all aggregators
            logger.info("Fetching all aggregators")
            aggregators = session.query(Aggregator).all()
            aggregators_dto = [
                DTO_Aggregator(
                    guid=aggregator.guid,
                    name=aggregator.name,
                    devices=[
                        DTO_Device(
                            name=device.name,
                            snapshots=[
                                DTO_Snapshot(
                                    timestamp_capture=datetime.fromtimestamp(snapshot.client_timestamp_epoch),
                                    timezone_mins=snapshot.client_timezon_mins,
                                    metrics=[
                                        DTO_Metric(
                                            name=metric.device_metric_type.name,
                                            value=metric.value
                                        ) for metric in snapshot.metrics
                                    ]
                                ) for snapshot in device.snapshots
                            ]
                        ) for device in aggregator.devices
                    ]
                ).to_dict() for aggregator in aggregators
            ]
            logger.info("Aggregators fetched")
            return jsonify(aggregators_dto), 200
    except Exception as e:
        logger.error(f"Error in get aggregator route: {e}")
        return jsonify({
                        "status": "error",
                        "message": str(e)
                        }), 500

@bp.route('/api/aggregator', methods=['GET', 'POST'])
def handle_aggregator():
    if request.method == 'POST':
        return add_aggregator()
    elif request.method == 'GET':
        return get_aggregator()

# @bp.route('/api/data', methods=['GET'])
# def get_data():
#     snapshots = Snapshot.query.all()
#     return jsonify([{
#         'device_id': snapshot.device_id,
#         'metric': snapshot.metric,
#         'timestamp_capture': snapshot.timestamp_capture
#     } for snapshot in snapshots])

# @bp.route('/api/data', methods=['POST'])
# def add_data():
#     data = request.get_json()
#     device_id = data.get('device_id')
#     metric = data.get('metric')
#     timestamp_capture = data.get('timestamp_capture')

#     if not device_id or not metric or not timestamp_capture:
#         return jsonify({"error": "Invalid data"}), 400

#     new_snapshot = Snapshot(
#         device_id=device_id,
#         metric=metric,
#         timestamp_capture=datetime.fromisoformat(timestamp_capture)
#     )
#     db.session.add(new_snapshot)
#     db.session.commit()

#     return jsonify({"message": "Data snapshot added successfully"}), 201