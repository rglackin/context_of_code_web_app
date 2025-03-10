from flask import Blueprint, jsonify, request
from models import *
from datetime import datetime
from dto_datamodel import DTO_Aggregator
from aggregator_mapping import map_dto_to_model
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dto_datamodel import *
import json

# Create blueprint - note we no longer need url_prefix here as it's defined in app.py
bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Root route for API
@bp.route('/')
def home():
    return jsonify({"message": "API is working - Dashboard is available at the root URL /"})

# Aggregator route - now at /api/aggregator because of the prefix in app.py
@bp.route('/aggregator', methods=['GET', 'POST'])
def handle_aggregator():
    if request.method == 'POST':
        return add_aggregator()
    elif request.method == 'GET':
        return get_aggregator()

def add_aggregator():
    try:
        session = db.session
        data = request.get_json()
        logger.info("Received data")
        if not data:
            logger.error("Invalid data received")
            return jsonify({"error": "Invalid data"}), 400
        
        logger.debug(data)
        # Deserialize JSON to DTO
        logger.info("Deserializing JSON to DTO")
        logger.debug(f"Data: {data}")
        aggregator_dto = DTO_Aggregator.from_json(data)
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
        
        aggregators = []
        if uuid:
            logger.info(f"Fetching aggregator with UUID: {uuid}")
            # Fetch a single aggregator by UUID
            aggregators = session.query(Aggregator).filter_by(guid=uuid)
            logger.info("Aggregator fetched")
            if not aggregators:
                return jsonify({"error": "Aggregator not found"}), 404
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
